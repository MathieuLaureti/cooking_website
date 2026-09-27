"""Redis-backed OAuth authorization codes and refresh tokens for MCP."""

from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any

from app.cache import cache

AUTH_CODE_TTL = int(os.getenv("MCP_OAUTH_CODE_TTL_SECONDS", "120"))
REFRESH_TTL = int(os.getenv("MCP_OAUTH_REFRESH_EXPIRE_SECONDS", "2592000"))

GEMINI_ENTERPRISE_REDIRECT_URI = "https://vertexaisearch.cloud.google.com/oauth-redirect"
# Gemini Spark (consumer) uses per-user redirect URIs under this prefix.
GEMINI_SPARK_REDIRECT_PREFIX = "https://oauth-redirect.googleusercontent.com/r/"

# Grok Bot / Cursor MCP (desktop loopback, Cloud Agents, Grok Bot cloud).
# DCR also sends cursor://anysphere.cursor-mcp/oauth/callback (legacy custom scheme).
CURSOR_MCP_REDIRECT_URIS = frozenset(
    {
        "https://www.cursor.com/agents/mcp/oauth/callback",
        "https://www.cursor.com/bot/mcp/oauth/callback",
        "http://localhost:8787/callback",
        "http://127.0.0.1:8787/callback",
    }
)
CURSOR_MCP_REDIRECT_PREFIX = "cursor://anysphere.cursor-mcp/oauth/"


def extra_redirect_uris() -> list[str]:
    raw = os.getenv("MCP_OAUTH_EXTRA_REDIRECT_URIS", "")
    return [u.strip() for u in raw.split(",") if u.strip()]


def allowed_redirect_uris(client_uris: list[str]) -> set[str]:
    allowed = {
        GEMINI_ENTERPRISE_REDIRECT_URI,
        *CURSOR_MCP_REDIRECT_URIS,
        *extra_redirect_uris(),
        *client_uris,
    }
    return allowed


def is_known_redirect_uri(redirect_uri: str) -> bool:
    """True if this URI may be registered (DCR) without an existing client record."""
    if redirect_uri in allowed_redirect_uris([]):
        return True
    if redirect_uri.startswith(GEMINI_SPARK_REDIRECT_PREFIX):
        return True
    if redirect_uri.startswith(CURSOR_MCP_REDIRECT_PREFIX):
        return True
    return False


def redirect_uri_allowed(redirect_uri: str, client_uris: list[str]) -> bool:
    if redirect_uri in allowed_redirect_uris(client_uris):
        return True
    if redirect_uri.startswith(GEMINI_SPARK_REDIRECT_PREFIX):
        return True
    if redirect_uri.startswith(CURSOR_MCP_REDIRECT_PREFIX):
        return True
    return False


@dataclass
class AuthCodeRecord:
    client_id: str
    user_id: int
    redirect_uri: str
    code_challenge: str
    scope: str
    resource: str | None = None


async def store_auth_code(record: AuthCodeRecord) -> str:
    code = secrets.token_urlsafe(32)
    payload = {
        "client_id": record.client_id,
        "user_id": record.user_id,
        "redirect_uri": record.redirect_uri,
        "code_challenge": record.code_challenge,
        "scope": record.scope,
        "resource": record.resource,
    }
    await cache.setex(f"oauth:code:{code}", AUTH_CODE_TTL, json.dumps(payload))
    return code


async def pop_auth_code(code: str) -> AuthCodeRecord | None:
    key = f"oauth:code:{code}"
    raw = await cache.get(key)
    if not raw:
        return None
    await cache.delete(key)
    data = json.loads(raw)
    return AuthCodeRecord(
        client_id=data["client_id"],
        user_id=int(data["user_id"]),
        redirect_uri=data["redirect_uri"],
        code_challenge=data["code_challenge"],
        scope=data.get("scope", "mcp"),
        resource=data.get("resource"),
    )


async def store_refresh_token(
    token: str, *, client_id: str, user_id: int, scope: str
) -> None:
    payload = json.dumps(
        {"client_id": client_id, "user_id": user_id, "scope": scope, "iat": time.time()}
    )
    await cache.setex(f"oauth:refresh:{token}", REFRESH_TTL, payload)


async def pop_refresh_token(token: str) -> dict[str, Any] | None:
    key = f"oauth:refresh:{token}"
    raw = await cache.get(key)
    if not raw:
        return None
    await cache.delete(key)
    return json.loads(raw)


async def get_refresh_token(token: str) -> dict[str, Any] | None:
    raw = await cache.get(f"oauth:refresh:{token}")
    if not raw:
        return None
    return json.loads(raw)


async def delete_refresh_token(token: str) -> None:
    await cache.delete(f"oauth:refresh:{token}")
