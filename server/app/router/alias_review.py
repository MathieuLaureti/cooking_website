from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alias_link import accept_review
from app.auth import TokenUser, require_admin
from app.database import get_db
from app.db_models.models import CatalogAliasReview
from app.ingredient_match import match_ingredient
from app.pydantic_models.alias_review import (
    AliasAccept,
    AliasMatchFood,
    AliasMatchRequest,
    AliasMatchResponse,
    AliasReviewItem,
)

router = APIRouter(prefix="/alias_reviews", tags=["Alias reviews"])


@router.get("", response_model=list[AliasReviewItem])
async def list_reviews(
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
    rows = (
        await db.execute(
            select(CatalogAliasReview)
            .where(CatalogAliasReview.status == "pending")
            .order_by(CatalogAliasReview.id)
        )
    ).scalars().all()
    return [
        AliasReviewItem(
            id=row.id,
            query=row.query,
            confidence=float(row.confidence) if row.confidence is not None else None,
            candidates=row.candidates,
        )
        for row in rows
    ]


@router.post("/match", response_model=AliasMatchResponse)
async def match_name(
    body: AliasMatchRequest,
    _admin: TokenUser = Depends(require_admin),
):
    query = body.query.strip()
    if not query or len(query) > 255:
        raise HTTPException(status_code=400, detail="Invalid name")
    try:
        result = await match_ingredient(query)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    food = None
    if result.food is not None:
        food = AliasMatchFood(
            id=result.food.id,
            name_en=result.food.name_en,
            name_fr=result.food.name_fr,
            group_en=result.food.group_en,
        )
    return AliasMatchResponse(status=result.status, confidence=result.confidence, match=food)


@router.post("/{review_id}/accept", response_model=AliasReviewItem)
async def accept(
    review_id: int,
    body: AliasAccept,
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
    try:
        review = await accept_review(db, review_id, body.food_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AliasReviewItem(
        id=review.id,
        query=review.query,
        confidence=float(review.confidence) if review.confidence is not None else None,
        candidates=review.candidates,
    )
