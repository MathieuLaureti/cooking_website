"""MCP (Model Context Protocol) HTTP endpoint for external AI clients."""

from __future__ import annotations

import logging
import re
from typing import Annotated

from fastapi import HTTPException
from fastmcp import FastMCP
from pydantic import Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.database import AsyncSessionLocal
from app.mcp_auth import validate_mcp_request
from app.mcp_sse_sanitize import SanitizeToolsListMiddleware
from app.mcp_tool_models import McpComponent, to_api_components
from app.pydantic_models import recipes as models

logger = logging.getLogger("uvicorn.error")

_MCP_METHOD_RE = re.compile(r'"method"\s*:\s*"([^"]+)"')


class _MCPAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        denied = validate_mcp_request(request)
        if denied is not None:
            return denied
        return await call_next(request)


class _MCPAuditMiddleware(BaseHTTPMiddleware):
    """Log JSON-RPC method names (helps confirm Gemini tools/call reaches the server)."""

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            body = await request.body()

            for match in _MCP_METHOD_RE.finditer(body.decode("utf-8", errors="replace")):
                logger.info("MCP JSON-RPC method=%s", match.group(1))

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            request = Request(request.scope, receive)
        elif request.method == "GET":
            sid = request.headers.get("mcp-session-id", "")
            logger.info("MCP GET stream request session=%s", bool(sid.strip()))
        response = await call_next(request)
        if request.url.path.rstrip("/").endswith("mcp") or "/mcp" in request.url.path:
            session = bool(request.headers.get("mcp-session-id", "").strip())
            logger.info(
                "MCP %s %s status=%s content-type=%s session=%s",
                request.method,
                request.url.path,
                response.status_code,
                response.headers.get("content-type", "-"),
                session,
            )
        return response


mcp = FastMCP(
    "cooking-website",
    instructions=(
        "Personal recipe catalog. dish_name = category (Pasta, Soup). "
        "recipe_name = one preparation under that dish. "
        "Always call create_recipe to persist; use ping to verify connectivity."
    ),
)


@mcp.tool(
    name="ping",
    description="Health check for MCP clients. Call this to verify the session can invoke tools.",
    output_schema=None,
)
async def ping() -> dict[str, str]:
    return {"status": "ok"}


@mcp.tool(
    name="create_recipe",
    title="create_recipe",
    description=(
        "Create a new recipe in the cooking catalog.\n\n"
        "Terminology (required):\n"
        "- dish_name: main category (e.g. Pasta, Soup). Matched or created.\n"
        "- recipe_name: specific recipe under that dish (e.g. Carbonara).\n\n"
        "components: one or more parts, each with ingredients (name, quantity, unit) "
        "and instructions (step number, text)."
    ),
    output_schema=None,
)
async def create_recipe(
    recipe_name: Annotated[
        str,
        Field(
            description="Name of this specific recipe (variant under the dish), not the dish category."
        ),
    ],
    dish_name: Annotated[
        str,
        Field(
            description="Main category name (dish). Matched to an existing dish or created if missing."
        ),
    ],
    components: Annotated[
        list[McpComponent],
        Field(
            min_length=1,
            description="Recipe parts: name, ingredients, numbered steps.",
        ),
    ],
) -> dict:
    from app.router.recipes import _create_recipe_in_db

    if not recipe_name.strip():
        raise ValueError("recipe_name is required")
    if not (dish_name or "").strip():
        raise ValueError("dish_name is required for the main category (dish)")

    async with AsyncSessionLocal() as db:
        try:
            recipe = await _create_recipe_in_db(
                recipe_name.strip(),
                to_api_components(components),
                db,
                dish_id=None,
                dish_name=dish_name.strip(),
            )
        except HTTPException as exc:
            detail = exc.detail
            if isinstance(detail, list):
                detail = "; ".join(str(d) for d in detail)
            raise ValueError(str(detail)) from exc

    payload = models.RecipeFull.model_validate(recipe).model_dump()
    return {
        "id": payload["id"],
        "name": payload["name"],
        "dish_id": payload["dish_id"],
        "components": payload["components"],
        "message": f"Created recipe '{payload['name']}' under dish id {payload['dish_id']}.",
    }


def build_mcp_asgi_app():
    # Stateful Streamable HTTP: Gemini uses GET SSE (mcp-session-id) after authenticated POST.
    # Prod gunicorn runs one worker so sessions stay in-process (see server/Dockerfile).
    app = mcp.http_app(
        path="/",
        transport="streamable-http",
        stateless_http=False,
    )
    app.add_middleware(_MCPAuditMiddleware)
    app.add_middleware(_MCPAuthMiddleware)
    wrapped = SanitizeToolsListMiddleware(app)
    if hasattr(app, "lifespan"):
        wrapped.lifespan = app.lifespan  # type: ignore[attr-defined]
    return wrapped
