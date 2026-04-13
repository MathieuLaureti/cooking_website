from pydantic import BaseModel, ConfigDict
from typing import List


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


class RecipeCreate(Recipe):
    components: List[Component]
