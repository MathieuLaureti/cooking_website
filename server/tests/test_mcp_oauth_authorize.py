"""MCP OAuth authorize redirect (RFC 9207 iss)."""

import base64
import hashlib
import secrets
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient

from app.mcp_oauth_config import mcp_resource_url, oauth_issuer

REDIRECT_URI = "http://127.0.0.1:8787/callback"


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


@pytest.mark.asyncio
async def test_authorize_redirect_includes_iss(
    client: AsyncClient, test_users: dict
) -> None:
    reg = await client.post(
        "/oauth/register",
        json={
            "redirect_uris": [REDIRECT_URI],
            "token_endpoint_auth_method": "none",
        },
    )
    assert reg.status_code == 201
    client_id = reg.json()["client_id"]
    verifier, challenge = _pkce_pair()
    admin = test_users["admin"]
    resource = mcp_resource_url()

    with patch(
        "app.router.mcp_oauth.store_auth_code",
        new=AsyncMock(return_value="test-auth-code"),
    ):
        response = await client.post(
            "/oauth/authorize",
            data={
                "username": admin.username,
                "password": "adminpass",
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": REDIRECT_URI,
                "state": "test-state",
                "scope": "mcp offline_access",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "resource": resource,
            },
            follow_redirects=False,
        )
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith(REDIRECT_URI)
    query = parse_qs(urlparse(location).query)
    assert query.get("code") == ["test-auth-code"]
    assert query.get("iss") == [oauth_issuer()]
    assert query.get("state") == ["test-state"]
    assert verifier  # PKCE pair built for authorize request
