"""Alias review accept/reject tests (issue #3)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.alias_link import queue_review
from app.db_models.models import CatalogFood
from tests.conftest import bearer


@pytest.mark.integration
@pytest.mark.asyncio
async def test_accept_invalid_food_id(
    client: AsyncClient,
    db_session: AsyncSession,
    test_users: dict,
    make_token,
) -> None:
    code = uuid.uuid4().hex[:8]
    food = CatalogFood(
        source="cnf",
        external_code=f"AR{code}",
        name_en="Test food",
        name_fr="Aliment test",
        group_en="Test",
    )
    db_session.add(food)
    await db_session.commit()
    await db_session.refresh(food)

    query = f"mystery ingredient {code}"
    review = await queue_review(
        db_session,
        query,
        0.5,
        [
            {
                "food_id": food.id,
                "name_en": food.name_en,
                "name_fr": food.name_fr,
            }
        ],
    )

    other = CatalogFood(
        source="cnf",
        external_code=f"AR2{code}",
        name_en="Other food",
        name_fr="Autre",
        group_en="Test",
    )
    db_session.add(other)
    await db_session.commit()
    await db_session.refresh(other)

    admin_token = make_token(test_users["admin"])
    bad = await client.post(
        f"/alias_reviews/{review.id}/accept",
        headers=bearer(admin_token),
        json={"food_id": other.id},
    )
    assert bad.status_code == 400

    good = await client.post(
        f"/alias_reviews/{review.id}/accept",
        headers=bearer(admin_token),
        json={"food_id": food.id},
    )
    assert good.status_code == 200
    assert good.json()["id"] == review.id

    missing = await client.post(
        f"/alias_reviews/{review.id}/accept",
        headers=bearer(admin_token),
        json={"food_id": food.id},
    )
    assert missing.status_code == 404
