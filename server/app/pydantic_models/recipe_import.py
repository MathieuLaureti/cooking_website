from datetime import datetime

from pydantic import BaseModel

from app.pydantic_models.recipes import RecipeExtract


class RecipeImportCreate(BaseModel):
    url: str


class RecipeImportItem(BaseModel):
    id: int
    url: str
    status: str
    extract: RecipeExtract | None = None
    error: str | None = None
    created_at: datetime
