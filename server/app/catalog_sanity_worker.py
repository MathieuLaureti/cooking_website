"""Background worker for admin-triggered catalog sanity preview runs."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.catalog_sanity import classify_foods, drop_to_dict
from app.database import AsyncSessionLocal
from app.db_models.models import CatalogSanityRun
from app.ingredient_match import load_foods

logger = logging.getLogger(__name__)

ACTIVE = ("queued", "running")


async def reset_running() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(CatalogSanityRun)
            .where(CatalogSanityRun.status == "running")
            .values(status="queued")
        )
        await session.commit()


async def claim_next() -> int | None:
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                select(CatalogSanityRun)
                .where(CatalogSanityRun.status == "queued")
                .order_by(CatalogSanityRun.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        row.status = "running"
        row.started_at = datetime.now(timezone.utc)
        await session.commit()
        return row.id


async def _set_progress(
    run_id: int,
    *,
    pipeline_layer: str,
    layer_current: int,
    layer_total: int,
    drops_count: int,
    total_foods: int | None = None,
) -> None:
    async with AsyncSessionLocal() as session:
        row = await session.get(CatalogSanityRun, run_id)
        if row is None or row.status != "running":
            return
        row.pipeline_layer = pipeline_layer
        row.layer_current = layer_current
        row.layer_total = layer_total
        row.drops_count = drops_count
        if total_foods is not None:
            row.total_foods = total_foods
        await session.commit()


async def _finish(
    run_id: int,
    *,
    status: str,
    result_drops: list[dict] | None,
    error: str | None,
) -> None:
    async with AsyncSessionLocal() as session:
        row = await session.get(CatalogSanityRun, run_id)
        if row is None:
            return
        row.status = status
        row.result_drops = result_drops
        row.error = error
        row.finished_at = datetime.now(timezone.utc)
        row.pipeline_layer = None
        await session.commit()


async def process_run(run_id: int) -> None:
    async with AsyncSessionLocal() as session:
        row = await session.get(CatalogSanityRun, run_id)
        if row is None or row.status != "running":
            return
        use_laya = row.use_laya

    foods = await load_foods()
    if not foods:
        await _finish(run_id, status="failed", result_drops=None, error="No CNF foods in catalog")
        return

    await _set_progress(
        run_id,
        pipeline_layer="Layer 1",
        layer_current=0,
        layer_total=len(foods),
        drops_count=0,
        total_foods=len(foods),
    )

    last_flush = 0.0

    async def on_progress(layer: str, current: int, total: int, drops_count: int) -> None:
        nonlocal last_flush
        now = time.monotonic()
        if layer == "Layer 3" and current not in (total,) and now - last_flush < 2.0:
            return
        last_flush = now
        await _set_progress(
            run_id,
            pipeline_layer=layer,
            layer_current=current,
            layer_total=total,
            drops_count=drops_count,
        )

    try:
        drops = await classify_foods(foods, use_laya=use_laya, on_progress=on_progress)
    except Exception as exc:
        logger.exception("Catalog sanity run %s failed", run_id)
        await _finish(run_id, status="failed", result_drops=None, error=str(exc)[:4000])
        return

    payload = [drop_to_dict(row) for row in drops]
    await _finish(run_id, status="completed", result_drops=payload, error=None)


async def catalog_sanity_worker() -> None:
    while True:
        try:
            await reset_running()
            break
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Catalog sanity worker could not reset running rows")
            await asyncio.sleep(2)
    while True:
        try:
            run_id = await claim_next()
            if run_id is None:
                await asyncio.sleep(1)
                continue
            await process_run(run_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Catalog sanity worker")
            await asyncio.sleep(1)
