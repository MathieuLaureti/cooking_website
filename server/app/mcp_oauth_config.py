"""Public OAuth / MCP URLs (PUBLIC_BASE_URL includes homelab /recipes prefix in prod)."""

from __future__ import annotations

import os


def public_base_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "http://localhost:81").rstrip("/")


def oauth_issuer() -> str:
    return public_base_url()


def mcp_resource_url() -> str:
    return f"{public_base_url()}/mcp/"


def oauth_protected_resource_metadata_url() -> str:
    return f"{public_base_url()}/.well-known/oauth-protected-resource"


def oauth_authorization_server_metadata_url() -> str:
    return f"{public_base_url()}/.well-known/oauth-authorization-server"


def oauth_authorize_url() -> str:
    return f"{public_base_url()}/oauth/authorize"


def oauth_token_url() -> str:
    return f"{public_base_url()}/oauth/token"


def oauth_register_url() -> str:
    return f"{public_base_url()}/oauth/register"


def mcp_oauth_enabled() -> bool:
    return bool(public_base_url())
