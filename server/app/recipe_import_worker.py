"""Claim queued URL imports one at a time and store the extract. Does not write recipes."""

import asyncio
import logging

from sqlalchemy import select, update

from app.database import AsyncSessionLocal
from app.db_models.models import RecipeUrlImport
from app.router.recipes import _dish_names, extractor

logger = logging.getLogger(__name__)
OPEN = ("queued", "running", "ready")


async def reset_running() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(RecipeUrlImport)
            .where(RecipeUrlImport.status == "running")
            .values(status="queued")
        )
        await session.commit()


async def claim_next() -> int | None:
    async with AsyncSessionLocal() as session:
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
        await session.commit()
        return job.id


async def _finish(job_id: int, *, status: str, extract: dict | None, error: str | None) -> None:
    async with AsyncSessionLocal() as session:
        job = await session.get(RecipeUrlImport, job_id)
        if job is None or job.status != "running":
            return
        job.status = status
        job.extract = extract
        job.error = error
        await session.commit()


async def process_job(job_id: int) -> None:
    async with AsyncSessionLocal() as session:
        job = await session.get(RecipeUrlImport, job_id)
        if job is None or job.status != "running":
            return
        url = job.url
        names = await _dish_names(session)
    try:
        extracted = await extractor.from_url(url, names)
    except Exception as exc:
        logger.exception("URL import %s failed", job_id)
        await _finish(job_id, status="failed", extract=None, error=str(exc)[:4000])
        return
    await _finish(
        job_id,
        status="ready",
        extract=extracted.model_dump(mode="json"),
        error=None,
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
