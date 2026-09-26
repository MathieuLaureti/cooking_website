"""MCP API key auth tests (issue #9)."""

import os

import pytest
from httpx import AsyncClient
from starlette.requests import Request

from app.mcp_auth import validate_mcp_request


def _request(method: str, path: str = "/mcp/", headers: dict[str, str] | None = None) -> Request:
    raw = headers or {}
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [(k.lower().encode(), v.encode()) for k, v in raw.items()],
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_mcp_post_without_key_returns_401(client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setenv("MCP_API_KEY", "test-mcp-key-ci")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    response = await client.post("/mcp/", json={})
    assert response.status_code == 401


def test_validate_mcp_request_api_key_mode(monkeypatch) -> None:
    monkeypatch.setenv("MCP_API_KEY", "secret-key")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    denied = validate_mcp_request(_request("POST"))
    assert denied is not None
    assert denied.status_code == 401

    allowed = validate_mcp_request(
        _request("POST", headers={"Authorization": "Bearer secret-key"})
    )
    assert allowed is None
