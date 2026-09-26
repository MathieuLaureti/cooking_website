"""Recipe URL import queue API tests (issue #17)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models.models import RecipeUrlImport
from tests.conftest import bearer


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retry_failed_import(
    client: AsyncClient,
    db_session: AsyncSession,
    test_users: dict,
    make_token,
) -> None:
    code = uuid.uuid4().hex[:8]
    row = RecipeUrlImport(
        url=f"https://example.com/recipe-{code}",
        normalized_url=f"https://example.com/recipe-{code}",
        status="failed",
        error="Extracted text too short",
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)

    admin_token = make_token(test_users["admin"])
    bad = await client.post(
        f"/recipe_imports/{row.id}/retry",
        headers=bearer(admin_token),
    )
    assert bad.status_code == 200
    body = bad.json()
    assert body["status"] == "queued"
    assert body["error"] is None
    assert body["extract"] is None

    again = await client.post(
        f"/recipe_imports/{row.id}/retry",
        headers=bearer(admin_token),
    )
    assert again.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retry_rejects_when_url_already_active(
    client: AsyncClient,
    db_session: AsyncSession,
    test_users: dict,
    make_token,
) -> None:
    code = uuid.uuid4().hex[:8]
    normalized = f"https://example.com/active-{code}"
    failed = RecipeUrlImport(
        url=normalized,
        normalized_url=normalized,
        status="failed",
        error="timeout",
    )
    queued = RecipeUrlImport(
        url=normalized,
        normalized_url=normalized,
        status="queued",
    )
    db_session.add_all([failed, queued])
    await db_session.commit()
    await db_session.refresh(failed)

    admin_token = make_token(test_users["admin"])
    res = await client.post(
        f"/recipe_imports/{failed.id}/retry",
        headers=bearer(admin_token),
    )
    assert res.status_code == 400
