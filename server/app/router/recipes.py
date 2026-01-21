import traceback
from fastapi import APIRouter, Depends, HTTPException, Security, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from app.database import get_db
from sqlalchemy import select, and_
from app.db_models.models import Dish, Recipe, RecipeComponent, Ingredient, Instruction
from app.pydantic_models import recipes as models
from typing import List
from ..scripts.APRWS import WebRecipeExtractor
from ..scripts.APRIR import ImageRecipeExtractor

router = APIRouter(prefix="/recipes", tags=[""])

def _create_recipe_in_db(payload: models.RecipeFull, dish_id: int, db: Session):
    """Internal helper to handle the SQLAlchemy mapping and commit."""
    receiving_dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not receiving_dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dish id : {dish_id} not found"
        )
        
    existing_recipe = db.query(Recipe).filter(
        Recipe.dish_id == dish_id, 
        Recipe.name == payload.name
    ).first()
    
    if existing_recipe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A recipe with name : {payload.name} already exists for this dish"
        )

    new_recipe = Recipe(
        name=payload.name,
        dish_id=dish_id,
        components=[
            RecipeComponent(
                name=component.name,
                instructions=[
                    Instruction(step=i.step, text=i.text)
                    for i in component.instructions
                ],
                ingredients=[
                    Ingredient(name=i.name, quantity=i.quantity, unit=i.unit)
                    for i in component.ingredients              
                ]
            ) for component in payload.components
        ]   
    )
    db.add(new_recipe)
    db.commit()
    db.refresh(new_recipe)
    return new_recipe

@router.post("/dish", response_model=models.DishSearch)
def new_dish(dish: models.DishBase, db = Depends(get_db)):
    existing_dish = db.query(Dish).filter(Dish.name == dish.name).first()

    if existing_dish:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dish with name '{dish.name}' already exists."
        )
    new_dish = Dish(
        name=dish.name
    )
    db.add(new_dish)
    db.commit()
    confirmation = db.query(Dish).filter(Dish.name == dish.name).first()
    return {
        "name": confirmation.name,
        "id": confirmation.id
        }

@router.put("/dish_edit/{dish_id}", response_model=models.DishSearch)
def edit_dish_by_id(dish_id: int, dish: models.DishBase, db: Session = Depends(get_db)):
    dish_exist = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish_exist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found"
        )
    dish_exist.name = dish.name
    db.commit()
    db.refresh(dish_exist)
    return {
        "name": dish_exist.name,
        "id": dish_exist.id
    }

@router.delete("/dish/{dish_id}")
async def delete_dish_by_id(dish_id: int, db: Session = Depends(get_db)):
    dish_exist = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish_exist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found"
        )
    recipe_in_dish = db.query(Recipe).filter(Recipe.dish_id == dish_id).first()
    if recipe_in_dish:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete dish with existing recipes. Please delete associated recipes first."
        )
    db.delete(dish_exist)
    db.commit()
    return {"detail": "Dish deleted successfully"}

@router.get("/searchList",response_model=List[models.DishSearch])
def get_dish_list(db = Depends(get_db)):
    return db.execute(select(Dish.id,Dish.name)).mappings().all()

@router.post("/recipe/{dish_id}", response_model=models.RecipeSearch)
def manual_new_recipe(payload: models.RecipeFull, dish_id: int, db: Session = Depends(get_db)):
    """Manually post a JSON recipe."""
    return _create_recipe_in_db(payload, dish_id, db)

@router.get("/recipe_list/{dish_id}")
def get_recipe_list_of_dish(dish_id: int,db = Depends(get_db)):
    return db.execute(select(Recipe.id,Recipe.name).where(Recipe.dish_id==dish_id)).mappings().all()

@router.get("/recipe/{dish_id}/{recipe_id}",response_model=models.RecipeFull)
def get_recipe_by_id(dish_id:int,recipe_id:int,db = Depends(get_db)):
    result = db.execute(select(Recipe).where(and_(Recipe.dish_id==dish_id,Recipe.id==recipe_id))).scalar()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found for this dish"
        )
    print(result)
    return result

OLLAMA_BASE = "http://192.168.2.99:11434/api/generate"
web_tool = WebRecipeExtractor(OLLAMA_BASE, "qwen2.5:7b")
img_tool = ImageRecipeExtractor(OLLAMA_BASE, "llama3.2-vision:11b")

@router.get("/recipe_url/{dish_id}", response_model=models.RecipeFull)
async def get_recipe_by_url(dish_id: int, url: str = Query(...), db: Session = Depends(get_db)):
    """Scrape a URL and save to DB."""
    try:
        # 1. AI Extraction
        data = await web_tool.extract(url, dish_id)
        # 2. DB Enscription
        return _create_recipe_in_db(data, dish_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/recipe/{recipe_id}")
async def delete_recipe_by_id(recipe_id: int, db: Session = Depends(get_db)):
    recipe_exist = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe_exist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    db.delete(recipe_exist)
    db.commit()
    return {"detail": "Recipe deleted successfully"}

@router.put("/recipe_edit/{recipe_id}", response_model=models.RecipeFull)
async def edit_recipe_by_id(payload: models.RecipeFull, recipe_id: int, db: Session = Depends(get_db)):
    recipe_exist = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe_exist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found"
        )
    # Update fields
    recipe_exist.name = payload.name
    # Clear existing components
    recipe_exist.components.clear()
    # Add updated components
    for component in payload.components:
        new_component = RecipeComponent(
            name=component.name,
            instructions=[
                Instruction(step=i.step, text=i.text)
                for i in component.instructions
            ],
            ingredients=[
                Ingredient(name=i.name, quantity=i.quantity, unit=i.unit)
                for i in component.ingredients              
            ]
        )
        recipe_exist.components.append(new_component)
    
    db.commit()
    db.refresh(recipe_exist)
    return recipe_exist