from pydantic import BaseModel, ConfigDict


class NutritionFoodShort(BaseModel):
    id: int
    name_en: str
    name_fr: str
    group_en: str | None = None

    model_config = ConfigDict(from_attributes=True)


class NutritionFoodPage(BaseModel):
    items: list[NutritionFoodShort]
    offset: int
    has_more: bool


class NutritionAmount(BaseModel):
    code: str
    symbol: str | None = None
    name_en: str
    name_fr: str
    unit: str
    decimals: int | None = None
    amount_per_100g: float


class NutritionFoodFull(NutritionFoodShort):
    group_fr: str | None = None
    nutrients: list[NutritionAmount]
