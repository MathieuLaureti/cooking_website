"""Auth and admin route tests (issue #2)."""

import pytest
from httpx import AsyncClient

from tests.conftest import bearer


@pytest.mark.integration
@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_registration_code_requires_admin(
    client: AsyncClient, test_users: dict, make_token
) -> None:
    user_token = make_token(test_users["user"])
    response = await client.get("/auth/registration-code", headers=bearer(user_token))
    assert response.status_code == 403

    admin_token = make_token(test_users["admin"])
    response = await client.get("/auth/registration-code", headers=bearer(admin_token))
    assert response.status_code == 200
    body = response.json()
    assert len(body["code"]) == 7
    assert body["expires_in_seconds"] > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, test_users: dict) -> None:
    admin = test_users["admin"]
    response = await client.post(
        "/auth/login",
        json={"username": admin.username, "password": "wrong"},
    )
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_and_me(client: AsyncClient, test_users: dict) -> None:
    admin = test_users["admin"]
    login = await client.post(
        "/auth/login",
        json={"username": admin.username, "password": "adminpass"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = await client.get("/auth/me", headers=bearer(token))
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_alias_list_requires_admin(
    client: AsyncClient, test_users: dict, make_token
) -> None:
    user_token = make_token(test_users["user"])
    response = await client.get("/alias_reviews", headers=bearer(user_token))
    assert response.status_code == 403
