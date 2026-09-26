from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenUser, get_current_user
from app.database import get_db
from app.db_models.models import CatalogAlias, CatalogFood, CatalogFoodNutrient, CatalogNutrient
from app.pydantic_models import nutrition
from app.seed_cnf import normalize_name

router = APIRouter(prefix="/nutrition", tags=["Nutrition"])

SOURCE = "cnf"
PAGE = 50


def _escape(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _like(term: str) -> str:
    return f"%{_escape(term)}%"


def _word_patterns(term: str) -> list[str]:
    escaped = _escape(term)
    return [escaped, f"{escaped} %", f"% {escaped}", f"% {escaped} %"]


@router.get("/foods", response_model=nutrition.NutritionFoodPage)
async def list_foods(
    q: str = Query("", max_length=80),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _user: TokenUser = Depends(get_current_user),
):
    raw = " ".join(q.split())
    normalized = normalize_name(raw)
    columns = (
        CatalogFood.id,
        CatalogFood.name_en,
        CatalogFood.name_fr,
        CatalogFood.group_en,
    )
    stmt = select(*columns).where(CatalogFood.source == SOURCE)
    if raw:
        if not normalized:
            return nutrition.NutritionFoodPage(items=[], offset=0, has_more=False)
        alias_pat = _like(normalized)
        raw_pat = _like(raw)
        word_hit = or_(
            *[CatalogFood.name_en.ilike(pattern, escape="\\") for pattern in _word_patterns(raw)],
            *[CatalogFood.name_fr.ilike(pattern, escape="\\") for pattern in _word_patterns(raw)],
            CatalogFood.aliases.any(
                or_(*[CatalogAlias.normalized.like(pattern, escape="\\") for pattern in _word_patterns(normalized)])
            ),
        )
        stmt = stmt.where(
            or_(
                CatalogFood.name_en.ilike(raw_pat, escape="\\"),
                CatalogFood.name_fr.ilike(raw_pat, escape="\\"),
                CatalogFood.aliases.any(CatalogAlias.normalized.ilike(alias_pat, escape="\\")),
            )
        ).order_by(case((word_hit, 0), else_=1), CatalogFood.name_en)
    else:
        stmt = stmt.order_by(CatalogFood.name_en)

    result = await db.execute(stmt.offset(offset).limit(PAGE + 1))
    rows = result.mappings().all()
    has_more = len(rows) > PAGE
    return nutrition.NutritionFoodPage(
        items=rows[:PAGE],
        offset=offset,
        has_more=has_more,
    )


@router.get("/foods/{food_id}", response_model=nutrition.NutritionFoodFull)
async def get_food(
    food_id: int,
    db: AsyncSession = Depends(get_db),
    _user: TokenUser = Depends(get_current_user),
):
    food = await db.scalar(
        select(CatalogFood).where(
            CatalogFood.id == food_id, CatalogFood.source == SOURCE
        )
    )
    if food is None:
        raise HTTPException(status_code=404, detail="Food not found")

    rows = await db.execute(
        select(
            CatalogNutrient.external_code,
            CatalogNutrient.symbol,
            CatalogNutrient.name_en,
            CatalogNutrient.name_fr,
            CatalogNutrient.unit,
            CatalogNutrient.decimals,
            CatalogFoodNutrient.amount_per_100g,
        )
        .join(CatalogFoodNutrient, CatalogFoodNutrient.nutrient_id == CatalogNutrient.id)
        .where(CatalogFoodNutrient.food_id == food.id)
        .order_by(CatalogNutrient.name_en)
    )
    nutrients = [
        nutrition.NutritionAmount(
            code=code,
            symbol=symbol,
            name_en=name_en,
            name_fr=name_fr,
            unit=unit,
            decimals=decimals,
            amount_per_100g=float(amount),
        )
        for code, symbol, name_en, name_fr, unit, decimals, amount in rows.all()
    ]
    return nutrition.NutritionFoodFull(
        id=food.id,
        name_en=food.name_en,
        name_fr=food.name_fr,
        group_en=food.group_en,
        group_fr=food.group_fr,
        nutrients=nutrients,
    )
