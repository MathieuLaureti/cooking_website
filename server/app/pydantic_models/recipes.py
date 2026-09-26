from pydantic import BaseModel, ConfigDict, field_validator
from typing import List, Any


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DishBase(BaseModel):
    name: str

    class Config:
        from_attributes = True


class DishSearch(DishBase):
    id: int


class Instruction(OrmBase):
    step: int
    text: str


class Ingredient(OrmBase):
    name: str
    quantity: str
    unit: str


class Recipe(BaseModel):
    dish_id: int
    name: str


class RecipeSearch(Recipe):
    id: int


class Component(OrmBase):
    name: str
    instructions: List[Instruction]
    ingredients: List[Ingredient]


class RecipeFull(OrmBase):
    id: int
    name: str
    dish_id: int
    components: List[Component]


class RecipeCreate(BaseModel):
    name: str
    components: List[Component]
    dish_id: int | None = None
    dish_name: str | None = None


class RecipeExtract(BaseModel):
    name: str
    dish_id: int | None = None
    dish_name: str = ""
    components: List[Component] = []


class ChatTurn(BaseModel):
    role: str
    text: str


class RecipeChatDraft(BaseModel):
    """Loose snapshot from the UI; coerces nulls and numeric quantities."""

    name: str = ""
    dish_id: int | None = None
    dish_name: str | None = None
    components: List[Component] = []

    @field_validator("dish_name", mode="before")
    @classmethod
    def empty_dish_name(cls, v: Any) -> str | None:
        if v is None or v == "":
            return None
        return str(v)

    @field_validator("components", mode="before")
    @classmethod
    def stringify_quantities(cls, components: Any) -> Any:
        if not isinstance(components, list):
            return components
        for comp in components:
            if not isinstance(comp, dict):
                continue
            for ing in comp.get("ingredients") or []:
                if isinstance(ing, dict) and ing.get("quantity") is not None:
                    ing["quantity"] = str(ing["quantity"])
        return components


class RecipeChatRequest(BaseModel):
    message: str
    dish_id: int | None = None
    history: List[ChatTurn] = []
    current_recipe: RecipeChatDraft | None = None


class RecipeChatResponse(BaseModel):
    reply: str
    recipes: List[RecipeExtract] = []
