from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from sqlalchemy import select
from app.db_models.models import MatchChecker
from app.pydantic_models import match_checker
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/match_checker", tags=["Match Checker"])


@router.get("/ingredients", response_model=List[match_checker.MatchCheckerShort])
async def get_ingredient_list(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MatchChecker.id, MatchChecker.title))
    return result.mappings().all()


@router.get("/ingredient/{id}", response_model=match_checker.MatchCheckerFull)
async def get_ingredient_by_id(id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(MatchChecker).where(MatchChecker.id == id)
    result = await db.execute(stmt)
    ingredient = result.scalar_one_or_none()

    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    return ingredient
