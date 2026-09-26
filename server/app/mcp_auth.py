"""MCP request authentication (OAuth access token or optional API key)."""

from __future__ import annotations

import logging
import os

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.auth import decode_mcp_access_token
from app.mcp_oauth_config import (
    mcp_oauth_enabled,
    oauth_protected_resource_metadata_url,
)

logger = logging.getLogger("uvicorn.error")

# Streamable HTTP session header (must match MCP SDK).
MCP_SESSION_ID_HEADER = "mcp-session-id"


def mcp_head_ok_response() -> Response:
    """Reachability probe (Gemini sends HEAD without Bearer). Still advertise OAuth."""
    headers: dict[str, str] = {}
    if mcp_oauth_enabled():
        metadata_url = oauth_protected_resource_metadata_url()
        headers["WWW-Authenticate"] = f'Bearer resource_metadata="{metadata_url}"'
    return Response(status_code=200, headers=headers)


def mcp_unauthorized_response() -> Response:
    if mcp_oauth_enabled():
        metadata_url = oauth_protected_resource_metadata_url()
        return Response(
            status_code=401,
            headers={
                "WWW-Authenticate": f'Bearer resource_metadata="{metadata_url}"',
            },
        )
    return JSONResponse({"error": "Unauthorized"}, status_code=401)


def mcp_disabled_response() -> Response:
    return JSONResponse(
        {"error": "MCP is disabled: set MCP_API_KEY or configure OAuth (PUBLIC_BASE_URL)"},
        status_code=503,
    )


def _log_auth_denied(request: Request, reason: str) -> None:
    has_bearer = request.headers.get("Authorization", "").startswith("Bearer ")
    session_id = request.headers.get(MCP_SESSION_ID_HEADER, "")
    logger.warning(
        "MCP auth denied method=%s reason=%s bearer=%s mcp-session-id=%s",
        request.method,
        reason,
        has_bearer,
        bool(session_id.strip()),
    )


def validate_mcp_request(request: Request) -> Response | None:
    """Return None if authorized; otherwise an error Response."""
    if request.method == "HEAD":
        return mcp_head_ok_response()

    # Gemini opens GET SSE with mcp-session-id after an authenticated POST; Bearer
    # is often omitted on GET. The MCP session manager binds auth at POST time.
    session_id = request.headers.get(MCP_SESSION_ID_HEADER, "").strip()
    if request.method in ("GET", "DELETE") and session_id:
        logger.info("MCP auth: allowing %s with session id", request.method)
        return None

    api_key = os.getenv("MCP_API_KEY", "").strip()
    auth = request.headers.get("Authorization", "")
    header_key = request.headers.get("X-MCP-API-Key", "")
    bearer = (
        auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
    )
    token = bearer or header_key.strip()

    if token and api_key and token == api_key:
        return None

    if bearer:
        user = decode_mcp_access_token(bearer)
        if user and user.role == "admin":
            return None

    if api_key:
        if not token:
            _log_auth_denied(request, "missing_token_api_key_mode")
            return mcp_unauthorized_response()
        _log_auth_denied(request, "invalid_token_api_key_mode")
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    if mcp_oauth_enabled():
        _log_auth_denied(request, "missing_or_invalid_oauth")
        return mcp_unauthorized_response()

    return mcp_disabled_response()
