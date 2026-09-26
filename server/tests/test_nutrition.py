"""Nutrition read path tests (issue #4)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models.models import CatalogFood, CatalogFoodNutrient, CatalogNutrient
from tests.conftest import bearer


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_food_by_id(
    client: AsyncClient,
    db_session: AsyncSession,
    test_users: dict,
    make_token,
) -> None:
    code = uuid.uuid4().hex[:8]
    food = CatalogFood(
        source="cnf",
        external_code=f"NU{code}",
        name_en="Test apple",
        name_fr="Pomme test",
        group_en="Fruit",
    )
    nutrient = CatalogNutrient(
        source="cnf",
        external_code=f"N{code}",
        name_en="Energy",
        name_fr="Énergie",
        unit="kcal",
        symbol="KCAL",
    )
    db_session.add_all([food, nutrient])
    await db_session.flush()
    db_session.add(
        CatalogFoodNutrient(
            food_id=food.id,
            nutrient_id=nutrient.id,
            amount_per_100g=52.0,
        )
    )
    await db_session.commit()

    token = make_token(test_users["user"])
    response = await client.get(
        f"/nutrition/foods/{food.id}",
        headers=bearer(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name_en"] == "Test apple"
    assert len(body["nutrients"]) == 1
    assert body["nutrients"][0]["amount_per_100g"] == 52.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_food_not_found(
    client: AsyncClient, test_users: dict, make_token
) -> None:
    token = make_token(test_users["user"])
    response = await client.get("/nutrition/foods/999999999", headers=bearer(token))
    assert response.status_code == 404
