from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenUser, require_admin
from app.catalog_sanity_worker import ACTIVE
from app.database import get_db
from app.db_models.models import CatalogSanityRun
from app.pydantic_models.catalog_sanity import (
    CatalogSanityDropItem,
    CatalogSanityRunCreate,
    CatalogSanityRunDetail,
    CatalogSanityRunItem,
)

router = APIRouter(prefix="/catalog_sanity", tags=["Catalog sanity"])


def _progress_label(row: CatalogSanityRun) -> str | None:
    if row.status not in ACTIVE and row.status != "completed":
        return None
    if row.pipeline_layer and row.layer_current is not None and row.layer_total is not None:
        return f"{row.pipeline_layer} - {row.layer_current}/{row.layer_total}"
    if row.status == "completed" and row.total_foods is not None:
        return f"Done — {row.drops_count} drops from {row.total_foods} foods"
    return None


def _item(row: CatalogSanityRun) -> CatalogSanityRunItem:
    return CatalogSanityRunItem(
        id=row.id,
        status=row.status,
        use_laya=row.use_laya,
        total_foods=row.total_foods,
        pipeline_layer=row.pipeline_layer,
        layer_current=row.layer_current,
        layer_total=row.layer_total,
        drops_count=row.drops_count,
        error=row.error,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
        progress_label=_progress_label(row),
    )


def _detail(row: CatalogSanityRun) -> CatalogSanityRunDetail:
    drops = None
    if row.result_drops is not None:
        drops = [CatalogSanityDropItem.model_validate(item) for item in row.result_drops]
    return CatalogSanityRunDetail(**_item(row).model_dump(), result_drops=drops)


async def _active_count(db: AsyncSession) -> int:
    return (
        await db.scalar(
            select(func.count())
            .select_from(CatalogSanityRun)
            .where(CatalogSanityRun.status.in_(ACTIVE))
        )
        or 0
    )


@router.get("/runs", response_model=list[CatalogSanityRunItem])
async def list_runs(
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
    rows = (
        await db.execute(
            select(CatalogSanityRun).order_by(CatalogSanityRun.id.desc()).limit(10)
        )
    ).scalars().all()
    return [_item(row) for row in rows]


@router.get("/runs/{run_id}", response_model=CatalogSanityRunDetail)
async def get_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
    row = await db.get(CatalogSanityRun, run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return _detail(row)


@router.post("/runs", response_model=CatalogSanityRunItem, status_code=status.HTTP_201_CREATED)
async def start_run(
    body: CatalogSanityRunCreate,
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
    if await _active_count(db) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A catalog sanity run is already queued or running",
        )
    row = CatalogSanityRun(status="queued", use_laya=body.use_laya)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _item(row)
