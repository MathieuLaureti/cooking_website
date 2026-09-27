"""MCP OAuth discovery metadata (RFC 8414 / Grok path-segment)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_oauth_authorization_server_metadata(client: AsyncClient) -> None:
    response = await client.get("/.well-known/oauth-authorization-server")
    assert response.status_code == 200
    body = response.json()
    assert "authorization_endpoint" in body
    assert "token_endpoint" in body
    assert "issuer" in body
    assert body.get("authorization_response_iss_parameter_supported") is True


@pytest.mark.asyncio
async def test_openid_configuration_not_served(client: AsyncClient) -> None:
    """Avoid OAuth AS JSON at an OIDC URL (Grok OIDC validation failure)."""
    response = await client.get("/.well-known/openid-configuration")
    assert response.status_code == 404
