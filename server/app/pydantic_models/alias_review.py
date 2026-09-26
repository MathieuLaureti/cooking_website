from pydantic import BaseModel


class AliasCandidate(BaseModel):
    food_id: int
    name_en: str
    name_fr: str
    probability: float | None = None


class AliasReviewItem(BaseModel):
    id: int
    query: str
    confidence: float | None = None
    candidates: list[AliasCandidate]


class AliasAccept(BaseModel):
    food_id: int


class AliasMatchRequest(BaseModel):
    query: str


class AliasMatchFood(BaseModel):
    id: int
    name_en: str
    name_fr: str
    group_en: str


class AliasMatchResponse(BaseModel):
    status: str
    confidence: float | None = None
    match: AliasMatchFood | None = None
