"""OAuth 2.0 authorization server + MCP protected resource metadata."""

from __future__ import annotations

import base64
import hashlib
import html
import secrets
from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_mcp_access_token,
    hash_client_secret,
    verify_client_secret,
    verify_password,
)
from app.database import get_db
from app.db_models.models import OAuthClient, User
from app.mcp_oauth_config import (
    mcp_resource_url,
    oauth_authorize_url,
    oauth_issuer,
    oauth_register_url,
    oauth_token_url,
)
from app.mcp_oauth_scopes import MCP_SCOPES_SUPPORTED, normalize_oauth_scope
from app.mcp_oauth_store import (
    AuthCodeRecord,
    is_known_redirect_uri,
    pop_auth_code,
    pop_refresh_token,
    redirect_uri_allowed,
    store_auth_code,
    store_refresh_token,
)

router = APIRouter(tags=["MCP OAuth"])


def _pkce_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    return _pkce_challenge(code_verifier) == code_challenge


async def _get_client(db: AsyncSession, client_id: str) -> OAuthClient | None:
    result = await db.execute(
        select(OAuthClient).where(OAuthClient.client_id == client_id)
    )
    return result.scalar_one_or_none()


def _client_credentials_from_token_request(
    request: Request, form: Any
) -> tuple[str | None, str | None]:
    client_id = form.get("client_id")
    client_secret = form.get("client_secret")
    cid = client_id.strip() if isinstance(client_id, str) and client_id.strip() else None
    csec = (
        client_secret.strip()
        if isinstance(client_secret, str) and client_secret.strip()
        else None
    )

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Basic "):
        try:
            decoded = base64.b64decode(auth.split(" ", 1)[1], validate=True).decode("utf-8")
            basic_id, sep, basic_secret = decoded.partition(":")
            if basic_id and not cid:
                cid = basic_id
            if sep and basic_secret and not csec:
                csec = basic_secret
        except (ValueError, UnicodeDecodeError):
            pass

    return cid, csec


def _verify_client_secret(
    client: OAuthClient,
    client_secret: str | None,
    *,
    grant_type: str | None = None,
    has_pkce: bool = False,
) -> bool:
    if client.token_endpoint_auth_method == "none":
        return True
    if client_secret:
        return verify_client_secret(client_secret, client.client_secret_hash)
    # Gemini Spark (OpenAuth) often uses PKCE without a client_secret on the token call.
    if grant_type == "authorization_code" and has_pkce:
        return True
    return False


@router.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata() -> dict[str, Any]:
    return {
        "resource": mcp_resource_url(),
        "authorization_servers": [oauth_issuer()],
        "scopes_supported": MCP_SCOPES_SUPPORTED,
        "bearer_methods_supported": ["header"],
    }


def _authorization_server_metadata() -> dict[str, Any]:
    return {
        "issuer": oauth_issuer(),
        "authorization_endpoint": oauth_authorize_url(),
        "token_endpoint": oauth_token_url(),
        "registration_endpoint": oauth_register_url(),
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": MCP_SCOPES_SUPPORTED,
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic",
            "none",
        ],
    }


@router.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_metadata() -> dict[str, Any]:
    return _authorization_server_metadata()


@router.post("/oauth/register")
async def dynamic_client_registration(
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    redirect_uris = body.get("redirect_uris") or []
    if not isinstance(redirect_uris, list) or not redirect_uris:
        raise HTTPException(400, "redirect_uris required")

    for uri in redirect_uris:
        if not isinstance(uri, str) or not is_known_redirect_uri(uri):
            raise HTTPException(400, f"redirect_uri not allowed: {uri}")

    client_id = secrets.token_urlsafe(16)
    client_secret = secrets.token_urlsafe(32)
    auth_method = body.get("token_endpoint_auth_method") or "none"
    if auth_method not in ("client_secret_post", "client_secret_basic", "none"):
        auth_method = "none"

    secret_hash = None if auth_method == "none" else hash_client_secret(client_secret)
    client = OAuthClient(
        client_id=client_id,
        client_secret_hash=secret_hash,
        client_name=body.get("client_name") or "MCP dynamic client",
        redirect_uris=list(redirect_uris),
        token_endpoint_auth_method=auth_method,
    )
    db.add(client)
    await db.commit()

    response: dict[str, Any] = {
        "client_id": client_id,
        "client_name": client.client_name,
        "redirect_uris": redirect_uris,
        "grant_types": body.get("grant_types") or ["authorization_code"],
        "response_types": body.get("response_types") or ["code"],
        "token_endpoint_auth_method": auth_method,
    }
    if client_secret and auth_method != "none":
        response["client_secret"] = client_secret
    return JSONResponse(response, status_code=201)


def _authorize_login_html(
    *,
    error: str | None,
    oauth_fields: dict[str, str],
) -> str:
    err = f'<p style="color:#f87171">{html.escape(error)}</p>' if error else ""
    hidden = "".join(
        f'<input type="hidden" name="{html.escape(k)}" value="{html.escape(v)}"/>'
        for k, v in oauth_fields.items()
        if v
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>Cooking MCP — Sign in</title></head>
<body style="font-family:system-ui;background:#4A594D;color:#F7F5F2;padding:2rem">
<div style="max-width:24rem;margin:auto;background:#374239;padding:2rem;border-radius:8px">
<h1 style="font-size:1.25rem;margin:0 0 1rem">Authorize MCP</h1>
<p style="font-size:0.75rem;opacity:0.8">Sign in with your Cooking admin account to connect this client (Gemini Spark, Grok Bot, Cursor).</p>
{err}
<form method="post" action="{html.escape(oauth_authorize_url())}">
{hidden}
<label>Username<br/><input name="username" required style="width:100%;padding:0.5rem;margin:0.5rem 0"/></label>
<label>Password<br/><input name="password" type="password" required style="width:100%;padding:0.5rem;margin:0.5rem 0"/></label>
<button type="submit" style="width:100%;padding:0.75rem;background:#FFA500;border:0;font-weight:bold;margin-top:0.5rem">Allow access</button>
</form>
</div></body></html>"""


@router.get("/oauth/authorize")
async def oauth_authorize_get(
    response_type: Annotated[str, Query()],
    client_id: Annotated[str, Query()],
    redirect_uri: Annotated[str, Query()],
    state: Annotated[str | None, Query()] = None,
    scope: Annotated[str | None, Query()] = None,
    code_challenge: Annotated[str | None, Query()] = None,
    code_challenge_method: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    if response_type != "code":
        raise HTTPException(400, "unsupported response_type")
    client = await _get_client(db, client_id)
    if not client:
        raise HTTPException(400, "invalid client_id")
    if not redirect_uri_allowed(redirect_uri, list(client.redirect_uris or [])):
        raise HTTPException(400, "invalid redirect_uri")
    if not code_challenge or code_challenge_method != "S256":
        raise HTTPException(400, "PKCE S256 required")

    oauth_fields = {
        "response_type": response_type,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state or "",
        "scope": normalize_oauth_scope(scope),
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }
    return HTMLResponse(_authorize_login_html(error=None, oauth_fields=oauth_fields))


@router.post("/oauth/authorize", response_model=None)
async def oauth_authorize_post(
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    response_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    state: Annotated[str, Form()] = "",
    scope: Annotated[str, Form()] = "mcp offline_access",
    code_challenge: Annotated[str, Form()] = "",
    code_challenge_method: Annotated[str, Form()] = "S256",
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    oauth_fields = {
        "response_type": response_type,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": scope,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }
    if response_type != "code":
        return HTMLResponse(
            _authorize_login_html(error="Unsupported response type.", oauth_fields=oauth_fields)
        )

    client = await _get_client(db, client_id)
    if not client or not redirect_uri_allowed(
        redirect_uri, list(client.redirect_uris or [])
    ):
        return HTMLResponse(
            _authorize_login_html(error="Invalid client or redirect URI.", oauth_fields=oauth_fields)
        )

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return HTMLResponse(
            _authorize_login_html(error="Invalid username or password.", oauth_fields=oauth_fields)
        )
    if user.role != "admin":
        return HTMLResponse(
            _authorize_login_html(
                error="Only admin accounts can authorize MCP access.",
                oauth_fields=oauth_fields,
            )
        )

    code = await store_auth_code(
        AuthCodeRecord(
            client_id=client_id,
            user_id=user.id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            scope=normalize_oauth_scope(scope),
        )
    )
    params: dict[str, str] = {"code": code}
    if state:
        params["state"] = state
    location = f"{redirect_uri}?{urlencode(params)}"
    return RedirectResponse(url=location, status_code=302)


@router.post("/oauth/token")
async def oauth_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    form = await request.form()
    grant_type = form.get("grant_type")
    client_id, client_secret = _client_credentials_from_token_request(request, form)

    if not client_id:
        raise HTTPException(400, "client_id required")
    client = await _get_client(db, client_id)
    if not client:
        raise HTTPException(401, "invalid_client")

    code_verifier = form.get("code_verifier")
    has_pkce = bool(code_verifier and str(code_verifier).strip())
    if not _verify_client_secret(
        client,
        client_secret,
        grant_type=str(grant_type) if grant_type else None,
        has_pkce=has_pkce,
    ):
        raise HTTPException(401, "invalid_client")

    if grant_type == "authorization_code":
        code = form.get("code")
        redirect_uri = form.get("redirect_uri")
        code_verifier = form.get("code_verifier")
        if not code or not redirect_uri or not code_verifier:
            raise HTTPException(400, "invalid_request")
        record = await pop_auth_code(str(code))
        if not record or record.client_id != client_id:
            raise HTTPException(400, "invalid_grant")
        if record.redirect_uri != redirect_uri:
            raise HTTPException(400, "invalid_grant")
        if not _verify_pkce(str(code_verifier), record.code_challenge):
            raise HTTPException(400, "invalid_grant")

        result = await db.execute(select(User).where(User.id == record.user_id))
        user = result.scalar_one_or_none()
        if not user or user.role != "admin":
            raise HTTPException(400, "invalid_grant")

        access = create_mcp_access_token(
            user.id,
            user.username,
            user.role,
            scope=record.scope,
            client_id=client_id,
        )
        body: dict[str, Any] = {
            "access_token": access,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": record.scope,
        }
        if "offline_access" in (record.scope or "").split():
            refresh = secrets.token_urlsafe(32)
            await store_refresh_token(
                refresh,
                client_id=client_id,
                user_id=user.id,
                scope=record.scope,
            )
            body["refresh_token"] = refresh
        return JSONResponse(body)

    if grant_type == "refresh_token":
        refresh_token = form.get("refresh_token")
        if not refresh_token:
            raise HTTPException(400, "invalid_request")
        stored = await pop_refresh_token(str(refresh_token))
        if not stored or stored.get("client_id") != client_id:
            raise HTTPException(400, "invalid_grant")
        result = await db.execute(select(User).where(User.id == int(stored["user_id"])))
        user = result.scalar_one_or_none()
        if not user or user.role != "admin":
            raise HTTPException(400, "invalid_grant")
        scope = stored.get("scope", "mcp")
        access = create_mcp_access_token(
            user.id,
            user.username,
            user.role,
            scope=scope,
            client_id=client_id,
        )
        new_refresh = secrets.token_urlsafe(32)
        await store_refresh_token(
            new_refresh,
            client_id=client_id,
            user_id=user.id,
            scope=scope,
        )
        return JSONResponse(
            {
                "access_token": access,
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": new_refresh,
                "scope": scope,
            }
        )

    raise HTTPException(400, "unsupported_grant_type")
