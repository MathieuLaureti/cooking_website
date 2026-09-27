"""OAuth / MCP public URL helpers."""

import os

import pytest

from app.mcp_oauth_config import mcp_resource_url, public_base_url


@pytest.fixture(autouse=True)
def _public_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://www.example.com/recipes")


def test_mcp_resource_url_has_no_trailing_slash() -> None:
    assert mcp_resource_url() == "https://www.example.com/recipes/mcp"
    assert not mcp_resource_url().endswith("/")


def test_public_base_url_strips_trailing_slash() -> None:
    os.environ["PUBLIC_BASE_URL"] = "https://www.example.com/recipes/"
    assert public_base_url() == "https://www.example.com/recipes"
