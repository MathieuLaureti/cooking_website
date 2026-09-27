"""Catalog sanity run API tests."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models.models import CatalogSanityRun
from tests.conftest import bearer


@pytest.mark.integration
@pytest.mark.asyncio
async def test_start_run_requires_admin(
    client: AsyncClient,
    test_users: dict,
    make_token,
) -> None:
    user_token = make_token(test_users["user"])
    denied = await client.post(
        "/catalog_sanity/runs",
        json={"use_laya": False},
        headers=bearer(user_token),
    )
    assert denied.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_start_and_list_run(
    client: AsyncClient,
    test_users: dict,
    make_token,
) -> None:
    admin_token = make_token(test_users["admin"])
    created = await client.post(
        "/catalog_sanity/runs",
        json={"use_laya": True},
        headers=bearer(admin_token),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "queued"
    assert body["use_laya"] is True

    conflict = await client.post(
        "/catalog_sanity/runs",
        json={"use_laya": False},
        headers=bearer(admin_token),
    )
    assert conflict.status_code == 409

    listed = await client.get("/catalog_sanity/runs", headers=bearer(admin_token))
    assert listed.status_code == 200
    rows = listed.json()
    assert rows[0]["id"] == body["id"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_run_detail(
    client: AsyncClient,
    db_session: AsyncSession,
    test_users: dict,
    make_token,
) -> None:
    row = CatalogSanityRun(
        status="completed",
        use_laya=False,
        total_foods=100,
        drops_count=2,
        result_drops=[
            {
                "food_id": 1,
                "layer": "layer1",
                "reason": "egg_fresh_raw",
                "name_en": "Egg, test",
                "name_fr": "Oeuf, test",
                "group_en": "Dairy and Egg Products",
            }
        ],
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)

    admin_token = make_token(test_users["admin"])
    detail = await client.get(
        f"/catalog_sanity/runs/{row.id}",
        headers=bearer(admin_token),
    )
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["drops_count"] == 2
    assert payload["result_drops"][0]["food_id"] == 1
    assert payload["progress_label"] is not None
