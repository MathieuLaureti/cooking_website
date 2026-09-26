import os

from app.mcp_oauth_config import mcp_resource_url


def test_mcp_resource_url_has_no_trailing_slash(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://www.homelabdu204.ca/recipes")
    assert mcp_resource_url() == "https://www.homelabdu204.ca/recipes/mcp"
