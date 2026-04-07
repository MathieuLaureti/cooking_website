from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
)
from sqlalchemy.orm import Session
from app.database import get_db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db_models.models import Dish, Recipe, RecipeComponent, Ingredient, Instruction
from app.pydantic_models import recipes as models
from typing import List
from ..scripts.APRWS import WebRecipeExtractor
from ..scripts.APRIR import ImageRecipeExtractor

router = APIRouter(prefix="/recipes", tags=[""])


async def _create_recipe_in_db(
    payload: models.RecipeCreate, dish_id: int, db: AsyncSession
):
    # Check for Dish existence
    dish_stmt = select(Dish).where(Dish.id == dish_id)
    dish_result = await db.execute(dish_stmt)
    if not dish_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dish id : {dish_id} not found",
        )

    # Check for existing Recipe
    recipe_stmt = select(Recipe).where(
        Recipe.dish_id == dish_id, Recipe.name == payload.name
    )
    recipe_result = await db.execute(recipe_stmt)
    if recipe_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A recipe with name : {payload.name} already exists for this dish",
        )

    # Construct object tree
    new_recipe = Recipe(
        name=payload.name,
        dish_id=dish_id,
        components=[
            RecipeComponent(
                name=comp.name,
                instructions=[
                    Instruction(step=i.step, text=i.text) for i in comp.instructions
                ],
                ingredients=[
                    Ingredient(name=i.name, quantity=i.quantity, unit=i.unit)
                    for i in comp.ingredients
                ],
            )
            for comp in payload.components
        ],
    )

    db.add(new_recipe)
    await db.commit()

    # Eager load relationships before returning to prevent lazy load errors during serialization
    stmt = (
        select(Recipe)
        .where(Recipe.id == new_recipe.id)
        .options(
            selectinload(Recipe.components).selectinload(RecipeComponent.instructions),
            selectinload(Recipe.components).selectinload(RecipeComponent.ingredients),
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one()


@router.post("/dish", response_model=models.DishSearch)
async def new_dish(dish: models.DishBase, db: AsyncSession = Depends(get_db)):
    stmt = select(Dish).where(Dish.name == dish.name)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dish with name '{dish.name}' already exists.",
        )

    new_dish_obj = Dish(name=dish.name)
    db.add(new_dish_obj)
    await db.commit()

    # Re-fetch for confirmation/ID
    stmt = select(Dish).where(Dish.name == dish.name)
    result = await db.execute(stmt)
    confirmation = result.scalar_one()
    return {"name": confirmation.name, "id": confirmation.id}


@router.put("/dish_edit/{dish_id}", response_model=models.DishSearch)
async def edit_dish_by_id(
    dish_id: int, dish: models.DishBase, db: AsyncSession = Depends(get_db)
):
    stmt = select(Dish).where(Dish.id == dish_id)
    result = await db.execute(stmt)
    dish_exist = result.scalar_one_or_none()

    if not dish_exist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dish not found"
        )

    dish_exist.name = dish.name
    await db.commit()
    # Manual attribute access works after commit if expire_on_commit=False
    # Otherwise, use a select stmt or await db.refresh(dish_exist)
    return {"name": dish_exist.name, "id": dish_exist.id}


@router.delete("/dish/{dish_id}")
async def delete_dish_by_id(dish_id: int, db: AsyncSession = Depends(get_db)):
    # Check for dish
    stmt_dish = select(Dish).where(Dish.id == dish_id)
    res_dish = await db.execute(stmt_dish)
    dish_exist = res_dish.scalar_one_or_none()

    if not dish_exist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dish not found"
        )

    # Check for recipes
    stmt_rec = select(Recipe).where(Recipe.dish_id == dish_id).limit(1)
    res_rec = await db.execute(stmt_rec)
    if res_rec.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete dish with existing recipes. Please delete associated recipes first.",
        )

    await db.delete(dish_exist)
    await db.commit()
    return {"detail": "Dish deleted successfully"}


@router.post("/recipe/{dish_id}", response_model=models.RecipeFull)
async def manual_new_recipe(
    payload: models.RecipeCreate, dish_id: int, db: AsyncSession = Depends(get_db)
):
    return await _create_recipe_in_db(payload, dish_id, db)


@router.get("/dishes", response_model=List[models.DishSearch])
async def get_dish_list(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dish.id, Dish.name))
    return result.mappings().all()


@router.get("/recipes/{dish_id}")
async def get_recipe_list_of_dish(dish_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Recipe.id, Recipe.name).where(Recipe.dish_id == dish_id)
    result = await db.execute(stmt)
    return result.mappings().all()


@router.get("/recipe/{recipe_id}", response_model=models.RecipeFull)
async def get_recipe_by_id(recipe_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.components).selectinload(RecipeComponent.instructions),
            selectinload(Recipe.components).selectinload(RecipeComponent.ingredients),
        )
    )

    result = await db.execute(stmt)
    recipe = result.scalar_one_or_none()

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found",
        )
    return recipe


OLLAMA_BASE = "http://192.168.2.99:11434/api/generate"
web_tool = WebRecipeExtractor(OLLAMA_BASE, "qwen2.5:7b")
img_tool = ImageRecipeExtractor(OLLAMA_BASE, "llama3.2-vision:11b")


@router.get("/recipe_url/{dish_id}", response_model=models.RecipeFull)
async def get_recipe_by_url(
    dish_id: int, url: str = Query(...), db: AsyncSession = Depends(get_db)
):
    try:
        data = await web_tool.extract(url, dish_id)
        return await _create_recipe_in_db(data, dish_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/recipe/{recipe_id}")
async def delete_recipe_by_id(recipe_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Recipe).where(Recipe.id == recipe_id)
    result = await db.execute(stmt)
    recipe_exist = result.scalar_one_or_none()

    if not recipe_exist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found"
        )

    await db.delete(recipe_exist)
    await db.commit()
    return {"detail": "Recipe deleted successfully"}


@router.put("/recipe_edit/{recipe_id}", response_model=models.RecipeFull)
async def edit_recipe_by_id(
    payload: models.RecipeFull, recipe_id: int, db: AsyncSession = Depends(get_db)
):
    # Fetch with components to allow clearing the collection
    stmt = (
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(selectinload(Recipe.components))
    )
    result = await db.execute(stmt)
    recipe_exist = result.scalar_one_or_none()

    if not recipe_exist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found"
        )

    recipe_exist.name = payload.name

    # In async, relationship manipulation requires the collection to be loaded
    recipe_exist.components.clear()

    for component in payload.components:
        new_component = RecipeComponent(
            name=component.name,
            instructions=[
                Instruction(step=i.step, text=i.text) for i in component.instructions
            ],
            ingredients=[
                Ingredient(name=i.name, quantity=i.quantity, unit=i.unit)
                for i in component.ingredients
            ],
        )
        recipe_exist.components.append(new_component)

    await db.commit()

    # Re-fetch tree for response serialization
    final_stmt = (
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.components).selectinload(RecipeComponent.instructions),
            selectinload(Recipe.components).selectinload(RecipeComponent.ingredients),
        )
    )
    final_result = await db.execute(final_stmt)
    return final_result.scalar_one()
