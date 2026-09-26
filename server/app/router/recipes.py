import re
import unicodedata
from typing import Any, Awaitable, Callable, List

import orjson
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import TokenUser, get_current_user, require_admin
from app.database import get_db
from app.db_models.models import Dish, Ingredient, Instruction, Recipe, RecipeComponent
from app.pydantic_models import recipes as models

from ..cache import cache
from ..scripts.extract import RecipeExtractor

router = APIRouter(prefix="/recipes", tags=[""])
extractor = RecipeExtractor()
_MAX_IMAGE_BYTES = 10 * 1024 * 1024


def _plain(name: str) -> str:
    decomposed = unicodedata.normalize("NFD", name)
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped).strip()


async def _dish_names(db: AsyncSession) -> list[str]:
    result = await db.execute(select(Dish.name).order_by(Dish.name))
    return [name for name in result.scalars().all() if name]


async def _dish_catalog(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(Dish.id, Dish.name).order_by(Dish.name))
    return [
        {"id": row.id, "name": row.name}
        for row in result
        if row.name
    ]


def _dish_context(dish_id: int | None, catalog: list[dict]) -> str:
    if dish_id is not None:
        match = next((d for d in catalog if d["id"] == dish_id), None)
        name = match["name"] if match else f"id {dish_id}"
        return f"The recipe is for the existing dish: {name} (id {dish_id}). Set dish_id to {dish_id}.\n\n"
    lines = "\n".join(f"- id {d['id']}: {d['name']}" for d in catalog) or "(none yet)"
    return (
        "Existing dishes (set dish_id to one of these ids when the recipe fits):\n"
        f"{lines}\n"
        "Otherwise set dish_name to a short new dish name.\n\n"
    )


async def _resolve_dish(
    db: AsyncSession, dish_id: int | None, dish_name: str | None
) -> tuple[Dish, bool]:
    if dish_id is not None:
        result = await db.execute(select(Dish).where(Dish.id == dish_id))
        dish = result.scalar_one_or_none()
        if not dish:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dish id : {dish_id} not found",
            )
        return dish, False

    cleaned = _plain(dish_name or "")
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dish name is required",
        )
    key = cleaned.casefold()

    async def match() -> Dish | None:
        result = await db.execute(select(Dish))
        for dish in result.scalars().all():
            if dish.name and _plain(dish.name).casefold() == key:
                return dish
        return None

    existing = await match()
    if existing:
        return existing, False

    dish = Dish(name=cleaned)
    db.add(dish)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        existing = await match()
        if existing:
            return existing, False
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dish with name '{cleaned}' already exists.",
        )
    return dish, True


async def _create_recipe_in_db(
    name: str,
    components: list[models.Component],
    db: AsyncSession,
    dish_id: int | None = None,
    dish_name: str | None = None,
):
    dish, created = await _resolve_dish(db, dish_id, dish_name)

    recipe_stmt = select(Recipe).where(Recipe.dish_id == dish.id, Recipe.name == name)
    recipe_result = await db.execute(recipe_stmt)
    if recipe_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A recipe with name : {name} already exists for this dish",
        )

    new_recipe = Recipe(
        name=name,
        dish_id=dish.id,
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
            for comp in components
        ],
    )

    db.add(new_recipe)
    await db.commit()
    await cache.delete(f"dish_recipes:{dish.id}")
    if created:
        await cache.delete("dishes:all")
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
async def new_dish(
    dish: models.DishBase,
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
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
    await cache.delete("dishes:all")

    # Re-fetch for confirmation/ID
    stmt = select(Dish).where(Dish.name == dish.name)
    result = await db.execute(stmt)
    confirmation = result.scalar_one()
    return {"name": confirmation.name, "id": confirmation.id}


@router.put("/dish_edit/{dish_id}", response_model=models.DishSearch)
async def edit_dish_by_id(
    dish_id: int,
    dish: models.DishBase,
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
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
    await cache.delete("dishes:all")
    # Manual attribute access works after commit if expire_on_commit=False
    # Otherwise, use a select stmt or await db.refresh(dish_exist)
    return {"name": dish_exist.name, "id": dish_exist.id}


@router.delete("/dish/{dish_id}")
async def delete_dish_by_id(
    dish_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
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
    await cache.delete("dishes:all")
    await cache.delete(f"dish_recipes:{dish_id}")
    return {"detail": "Dish deleted successfully"}


async def fetch_with_cache(
    cache_key: str, ttl: int, fetch_func: Callable[[], Awaitable[Any]]
) -> Any:
    """Handles cache-aside pattern to reduce boilerplate and prevent sync blocking."""
    cached = await cache.get(cache_key)
    if cached:
        return orjson.loads(cached)

    data = await fetch_func()
    # orjson.dumps returns bytes, which Redis async client handles natively
    await cache.setex(cache_key, ttl, orjson.dumps(data))
    return data


@router.post("/recipe/{dish_id}", response_model=models.RecipeFull)
async def manual_new_recipe(
    payload: models.RecipeCreate,
    dish_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
    return await _create_recipe_in_db(
        payload.name, payload.components, db, dish_id=dish_id
    )


@router.post("/recipe", response_model=models.RecipeFull)
async def manual_new_recipe_by_name(
    payload: models.RecipeCreate,
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
    return await _create_recipe_in_db(
        payload.name,
        payload.components,
        db,
        dish_id=payload.dish_id or None,
        dish_name=payload.dish_name,
    )


@router.get("/dishes", response_model=List[models.DishSearch])
async def get_dish_list(
    db: AsyncSession = Depends(get_db),
    _user: TokenUser = Depends(get_current_user),
):
    async def fetch_data():
        result = await db.execute(
            select(Dish.id, Dish.name).order_by(Dish.name)
        )
        return [dict(r) for r in result.mappings().all()]

    return await fetch_with_cache("dishes:all", 3600, fetch_data)


@router.get("/recipes/{dish_id}")
async def get_recipe_list_of_dish(
    dish_id: int,
    db: AsyncSession = Depends(get_db),
    _user: TokenUser = Depends(get_current_user),
):
    async def fetch_data():
        stmt = (
            select(Recipe.id, Recipe.name)
            .where(Recipe.dish_id == dish_id)
            .order_by(Recipe.name)
        )
        result = await db.execute(stmt)
        return [dict(r) for r in result.mappings().all()]

    return await fetch_with_cache(f"dish_recipes:{dish_id}", 3600, fetch_data)


@router.get("/recipe/{recipe_id}", response_model=models.RecipeFull)
async def get_recipe_by_id(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
    _user: TokenUser = Depends(get_current_user),
):
    async def fetch_data():
        stmt = (
            select(Recipe)
            .where(Recipe.id == recipe_id)
            .options(
                selectinload(Recipe.components).selectinload(
                    RecipeComponent.instructions
                ),
                selectinload(Recipe.components).selectinload(
                    RecipeComponent.ingredients
                ),
            )
        )
        result = await db.execute(stmt)
        recipe = result.scalar_one_or_none()

        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipe not found",
            )
        return models.RecipeFull.model_validate(recipe).model_dump()

    return await fetch_with_cache(f"full_recipe:{recipe_id}", 3600, fetch_data)


def _image_mime(data: bytes, content_type: str | None) -> str:
    if content_type and content_type.startswith("image/"):
        mime = content_type.split(";", 1)[0].strip()
        return "image/jpeg" if mime == "image/jpg" else mime
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"GIF8"):
        return "image/gif"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image"
    )


async def _import_extracted(extracted, db: AsyncSession, dish_id: int | None):
    return await _create_recipe_in_db(
        extracted.name,
        extracted.components,
        db,
        dish_id=dish_id,
        dish_name=None if dish_id is not None else extracted.dish_name,
    )


@router.get("/recipe_url", response_model=models.RecipeFull)
async def get_recipe_by_url(
    url: str = Query(...),
    dish_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
    try:
        names = None if dish_id is not None else await _dish_names(db)
        extracted = await extractor.from_url(url, names)
        return await _import_extracted(extracted, db, dish_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recipe_image", response_model=models.RecipeFull)
async def recipe_from_image(
    file: UploadFile = File(...),
    dish_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
    raw = await file.read()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty image"
        )
    if len(raw) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Image too large"
        )
    mime = _image_mime(raw, file.content_type)
    try:
        names = None if dish_id is not None else await _dish_names(db)
        extracted = await extractor.from_image(raw, mime, names)
        return await _import_extracted(extracted, db, dish_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recipe_chat", response_model=models.RecipeChatResponse)
async def recipe_chat(
    payload: models.RecipeChatRequest,
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
    catalog = await _dish_catalog(db)
    context = _dish_context(payload.dish_id, catalog)
    try:
        reply, recipes = await extractor.chat(payload, context)
        return models.RecipeChatResponse(reply=reply, recipes=recipes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/recipe/{recipe_id}")
async def delete_recipe_by_id(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
):
    stmt = select(Recipe).where(Recipe.id == recipe_id)
    result = await db.execute(stmt)
    recipe_exist = result.scalar_one_or_none()

    if not recipe_exist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found"
        )

    dish_id = recipe_exist.dish_id
    await db.delete(recipe_exist)
    await db.commit()
    await cache.delete(f"dish_recipes:{dish_id}")
    await cache.delete(f"full_recipe:{recipe_id}")
    return {"detail": "Recipe deleted successfully"}


@router.put("/recipe_edit/{recipe_id}", response_model=models.RecipeFull)
async def edit_recipe_by_id(
    payload: models.RecipeFull,
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: TokenUser = Depends(require_admin),
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
    await cache.delete(f"full_recipe:{recipe_id}")
    await cache.delete(f"dish_recipes:{recipe_exist.dish_id}")

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
