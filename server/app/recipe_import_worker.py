"""Claim queued URL imports one at a time and store the extract. Does not write recipes."""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.database import AsyncSessionLocal
from app.db_models.models import RecipeUrlImport
from app.gemini_scheduler import GeminiPriority
from app.recipe_import_limits import (
    ai_backoff_seconds,
    is_retryable_gemini_error,
)
from app.scripts.extract import PAGE_CHAR_CAP, PageFetchResult, RecipeExtractor
from app.router.recipes import _dish_names

logger = logging.getLogger(__name__)
extractor = RecipeExtractor()


async def reset_running() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(RecipeUrlImport)
            .where(RecipeUrlImport.status == "running")
            .values(status="queued")
        )
        await session.commit()


async def claim_next() -> int | None:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        due_ai = (
            await session.execute(
                select(RecipeUrlImport)
                .where(
                    RecipeUrlImport.status == "ai_wait",
                    RecipeUrlImport.ai_next_attempt_at <= now,
                )
                .order_by(RecipeUrlImport.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        ).scalar_one_or_none()
        job = due_ai
        if job is None:
            job = (
                await session.execute(
                    select(RecipeUrlImport)
                    .where(RecipeUrlImport.status == "queued")
                    .order_by(RecipeUrlImport.id)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
            ).scalar_one_or_none()
        if job is None:
            return None
        job.status = "running"
        job.error = None
        if job.page_text:
            job.pipeline_step = 3
        else:
            job.pipeline_step = 1
        await session.commit()
        return job.id


async def _set_step(job_id: int, step: int) -> None:
    async with AsyncSessionLocal() as session:
        job = await session.get(RecipeUrlImport, job_id)
        if job is None:
            return
        job.pipeline_step = step
        await session.commit()


async def _save_fetch(job_id: int, fetched: PageFetchResult) -> None:
    text = fetched.text[:PAGE_CHAR_CAP]
    async with AsyncSessionLocal() as session:
        job = await session.get(RecipeUrlImport, job_id)
        if job is None or job.status != "running":
            return
        job.page_text = text
        job.structured_ingredients = fetched.structured_ingredients or None
        job.pipeline_step = 3
        await session.commit()


async def _finish(
    job_id: int,
    *,
    status: str,
    extract: dict | None,
    error: str | None,
    clear_cache: bool = False,
) -> None:
    async with AsyncSessionLocal() as session:
        job = await session.get(RecipeUrlImport, job_id)
        if job is None or job.status not in ("running", "ai_wait"):
            return
        job.status = status
        job.extract = extract
        job.error = error
        job.pipeline_step = None
        job.ai_next_attempt_at = None
        if status == "ready":
            job.ai_attempt_count = 0
        if clear_cache or status in ("ready", "failed"):
            job.page_text = None
            job.structured_ingredients = None
        await session.commit()


async def _defer_ai(job_id: int, message: str, attempt_count: int) -> None:
    from datetime import timedelta

    delay = ai_backoff_seconds(attempt_count)
    if delay is None:
        await _finish(job_id, status="failed", extract=None, error=message[:4000], clear_cache=True)
        return
    when = datetime.now(timezone.utc) + timedelta(seconds=delay)
    async with AsyncSessionLocal() as session:
        job = await session.get(RecipeUrlImport, job_id)
        if job is None:
            return
        job.status = "ai_wait"
        job.pipeline_step = 3
        job.error = message[:4000]
        job.ai_attempt_count = attempt_count + 1
        job.ai_next_attempt_at = when
        await session.commit()


async def process_job(job_id: int) -> None:
    async with AsyncSessionLocal() as session:
        job = await session.get(RecipeUrlImport, job_id)
        if job is None or job.status != "running":
            return
        url = job.url
        cached = job.page_text
        structured = job.structured_ingredients or []
        names = await _dish_names(session)
        attempt = job.ai_attempt_count

    if cached:
        fetched = PageFetchResult(cached, list(structured) if structured else [])
    else:
        try:
            await _set_step(job_id, 1)
            fetched = await extractor.fetch_page_for_import(url)
            await _set_step(job_id, 2)
            await _save_fetch(job_id, fetched)
        except Exception as exc:
            logger.exception("URL import %s fetch failed", job_id)
            await _finish(job_id, status="failed", extract=None, error=str(exc)[:4000], clear_cache=True)
            return

    try:
        extracted = await extractor.extract_from_cached_page(
            fetched,
            names,
            priority=GeminiPriority.BACKGROUND,
        )
    except Exception as exc:
        msg = str(exc)
        if is_retryable_gemini_error(msg):
            logger.warning("URL import %s AI deferred: %s", job_id, msg[:200])
            await _defer_ai(job_id, msg, attempt)
            return
        logger.exception("URL import %s failed", job_id)
        await _finish(job_id, status="failed", extract=None, error=msg[:4000], clear_cache=True)
        return

    await _finish(
        job_id,
        status="ready",
        extract=extracted.model_dump(mode="json"),
        error=None,
        clear_cache=True,
    )


async def import_worker() -> None:
    while True:
        try:
            await reset_running()
            break
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("URL import worker could not reset running rows")
            await asyncio.sleep(2)
    while True:
        try:
            job_id = await claim_next()
            if job_id is None:
                await asyncio.sleep(1)
                continue
            await process_job(job_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("URL import worker")
            await asyncio.sleep(1)
