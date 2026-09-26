from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenUser, require_admin
from app.database import get_db
from app.db_models.models import RecipeUrlImport
from app.pydantic_models.recipe_import import RecipeImportCreate, RecipeImportItem
from app.pydantic_models.recipes import RecipeExtract
from app.router.recipes import _import_extracted

router = APIRouter(prefix="/recipe_imports", tags=["Recipe imports"])
ACTIVE = ("queued", "running", "ready")


def normalize_url(raw: str) -> str:
    parsed = urlsplit(raw.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must start with http:// or https://")
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


def _item(row: RecipeUrlImport) -> RecipeImportItem:
    extract = RecipeExtract.model_validate(row.extract) if row.extract else None
    return RecipeImportItem(
        id=row.id,
        url=row.url,
        status=row.status,
        extract=extract,
        error=row.error,
        created_at=row.created_at,
    )


async def _active(db: AsyncSession, normalized: str) -> RecipeUrlImport | None:
    return await db.scalar(
        select(RecipeUrlImport).where(
            RecipeUrlImport.normalized_url == normalized,
            RecipeUrlImport.status.in_(ACTIVE),
        )
    )


@router.get("", response_model=list[RecipeImportItem])
async def list_imports(
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
    rows = (
        await db.execute(
            select(RecipeUrlImport)
            .where(RecipeUrlImport.status.notin_(("kept", "discarded")))
            .order_by(RecipeUrlImport.id)
        )
    ).scalars().all()
    return [_item(row) for row in rows]


@router.post("", response_model=RecipeImportItem)
async def enqueue(
    body: RecipeImportCreate,
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
    raw = body.url.strip()
    if not raw or len(raw) > 2048:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid URL")
    try:
        normalized = normalize_url(raw)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    existing = await _active(db, normalized)
    if existing is not None:
        return _item(existing)
    row = RecipeUrlImport(url=raw, normalized_url=normalized, status="queued")
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await _active(db, normalized)
        if existing is not None:
            return _item(existing)
        raise
    await db.refresh(row)
    return _item(row)


@router.post("/{import_id}/keep", response_model=RecipeImportItem)
async def keep(
    import_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
    row = await db.get(RecipeUrlImport, import_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found")
    if row.status != "ready" or not row.extract:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Import is not ready")
    extracted = RecipeExtract.model_validate(row.extract)
    recipe = await _import_extracted(extracted, db, None)
    row.status = "kept"
    row.recipe_id = recipe.id
    await db.commit()
    await db.refresh(row)
    return _item(row)


@router.post("/{import_id}/discard", response_model=RecipeImportItem)
async def discard(
    import_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
    row = await db.get(RecipeUrlImport, import_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found")
    if row.status not in {"ready", "failed"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Import cannot be discarded")
    row.status = "discarded"
    await db.commit()
    await db.refresh(row)
    return _item(row)
