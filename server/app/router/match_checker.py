from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.orm import Session
from app.database import get_db
from sqlalchemy import select
from app.db_models.models import MatchChecker
from app.pydantic_models import match_checker
from typing import List

router = APIRouter(prefix="/match_checker", tags=["Match Checker"])

@router.get("/ingredient_list",response_model=List[match_checker.MatchCheckerShort])
def get_ingredient_list(db: Session = Depends(get_db)):
    return db.execute(select(MatchChecker.id,MatchChecker.title)).mappings().all()
    
@router.get("/get_ingredient/{id}", response_model=match_checker.MatchCheckerFull)
def get_ingredient_by_id(id: int, db: Session = Depends(get_db)):
    result = db.execute(select(MatchChecker).where(MatchChecker.id == id)).scalar_one_or_none()
    if not result:
            raise HTTPException(status_code=404, detail="Ingredient not found")       
    return result