"""Smoke tests for the pytest harness (issue #1)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == "Hello World"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_db_session_select_one(db_session: AsyncSession) -> None:
    result = await db_session.execute(text("SELECT 1 AS n"))
    assert result.scalar_one() == 1
