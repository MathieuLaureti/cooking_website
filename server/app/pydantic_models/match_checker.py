from pydantic import BaseModel, ConfigDict
from typing import List, Tuple

class IngredientMCSchema(BaseModel):
    title: str
    avoid: List[str]
    affinities: List[str]
    matches: List[Tuple[str, int]]

    class Config:
        from_attributes = True


class MatchCheckerBase(BaseModel):
    title: str
    model_config = ConfigDict(from_attributes=True)

class MatchCheckerShort(MatchCheckerBase):
    id: int

class MatchCheckerFull(MatchCheckerShort):
    avoid: List[str]
    affinities: List[str]
    matches: List[Tuple[str, int]]
