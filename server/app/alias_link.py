"""Save a typed name as a catalog alias, or leave it on the admin review queue."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models.models import CatalogAlias, CatalogAliasReview, CatalogFood
from app.seed_cnf import normalize_name


def alias_locale(raw: str, name_en: str, name_fr: str) -> str:
    words = set(normalize_name(raw).split())
    french = len(words & set(normalize_name(name_fr).split()))
    english = len(words & set(normalize_name(name_en).split()))
    return "fr" if french > english else "en"


async def link_alias(
    session: AsyncSession,
    raw: str,
    food_id: int,
    name_en: str,
    name_fr: str,
) -> None:
    normalized = normalize_name(raw)
    if not normalized:
        return
    existing = await session.scalar(
        select(CatalogAlias).where(CatalogAlias.normalized == normalized)
    )
    if existing is not None:
        return
    session.add(
        CatalogAlias(
            food_id=food_id,
            name=raw.strip()[:255],
            normalized=normalized,
            locale=alias_locale(raw, name_en, name_fr),
        )
    )
    await session.commit()


async def queue_review(
    session: AsyncSession,
    raw: str,
    confidence: float | None,
    candidates: list[dict],
) -> CatalogAliasReview:
    normalized = normalize_name(raw)
    row = await session.scalar(
        select(CatalogAliasReview).where(CatalogAliasReview.normalized == normalized)
    )
    if row is None:
        row = CatalogAliasReview(
            query=raw.strip()[:255],
            normalized=normalized,
            candidates=candidates,
            confidence=confidence,
            status="pending",
        )
        session.add(row)
    elif row.status != "resolved":
        row.query = raw.strip()[:255]
        row.candidates = candidates
        row.confidence = confidence
        row.status = "pending"
        row.food_id = None
    await session.commit()
    await session.refresh(row)
    return row


async def accept_review(session: AsyncSession, review_id: int, food_id: int) -> CatalogAliasReview:
    review = await session.get(CatalogAliasReview, review_id)
    if review is None or review.status != "pending":
        raise LookupError("Review not found")
    allowed = {item["food_id"] for item in review.candidates}
    if food_id not in allowed:
        raise ValueError("Food is not one of the choices")
    food = await session.get(CatalogFood, food_id)
    if food is None:
        raise LookupError("Food not found")
    await link_alias(session, review.query, food.id, food.name_en, food.name_fr)
    review.status = "resolved"
    review.food_id = food.id
    await session.commit()
    await session.refresh(review)
    return review
