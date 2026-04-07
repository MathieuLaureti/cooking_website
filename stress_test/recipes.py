from pydantic import BaseModel
from typing import List


class DishBase(BaseModel):
    name: str

    class Config:
        from_attributes = True


class DishSearch(DishBase):
    id: int


class Instruction(BaseModel):
    step: int
    text: str


class Ingredient(BaseModel):
    name: str
    quantity: str
    unit: str


class Recipe(BaseModel):
    dish_id: int
    name: str


class RecipeSearch(Recipe):
    id: int


class Component(BaseModel):
    name: str
    instructions: List[Instruction]
    ingredients: List[Ingredient]


class RecipeFull(Recipe):
    id: int
    components: List[Component]


class RecipeCreate(Recipe):
    components: List[Component]
