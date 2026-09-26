"""Ensure optional env-configured OAuth client exists for Gemini Advanced features."""

from __future__ import annotations

import asyncio
import os
import secrets

from sqlalchemy import select

from app.auth import hash_client_secret
from app.database import AsyncSessionLocal
from app.db_models.models import OAuthClient
from app.mcp_oauth_store import GEMINI_ENTERPRISE_REDIRECT_URI


async def ensure_env_oauth_client() -> None:
    client_id = os.getenv("MCP_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("MCP_OAUTH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OAuthClient).where(OAuthClient.client_id == client_id)
        )
        client = result.scalar_one_or_none()
        secret_hash = hash_client_secret(client_secret)
        uris = [GEMINI_ENTERPRISE_REDIRECT_URI]
        if client:
            client.client_secret_hash = secret_hash
            client.redirect_uris = list(set([*(client.redirect_uris or []), *uris]))
            client.client_name = client.client_name or "Gemini (env)"
            # Spark exchanges tokens with PKCE only (OpenAuth); keep hash for manual tests.
            client.token_endpoint_auth_method = "none"
        else:
            db.add(
                OAuthClient(
                    client_id=client_id,
                    client_secret_hash=secret_hash,
                    client_name="Gemini (env)",
                    redirect_uris=uris,
                    token_endpoint_auth_method="none",
                )
            )
        await db.commit()


def generate_oauth_client_credentials() -> tuple[str, str]:
    return secrets.token_urlsafe(16), secrets.token_urlsafe(32)


def main() -> None:
    asyncio.run(ensure_env_oauth_client())


if __name__ == "__main__":
    main()
