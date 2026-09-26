"""OAuth scopes for Gemini Spark MCP (see Google AI Developers Forum compatibility notes)."""

from __future__ import annotations

# Spark may require this scope in metadata + token response to inject MCP tools into chat.
GEMINI_MCP_CONTENT_SCOPE = "ACCESS_VIEW_MANAGE_MCP_CONTENT"

MCP_SCOPES_SUPPORTED = [
    "mcp",
    "offline_access",
    GEMINI_MCP_CONTENT_SCOPE,
]

_ALLOWED = frozenset(MCP_SCOPES_SUPPORTED)


def normalize_oauth_scope(scope: str | None) -> str:
    """Keep allowed scopes; always grant Gemini compatibility scope for Spark."""
    parts = (scope or "mcp offline_access").split()
    granted = [p for p in parts if p in _ALLOWED]
    if "mcp" not in granted:
        granted.insert(0, "mcp")
    if GEMINI_MCP_CONTENT_SCOPE not in granted:
        granted.append(GEMINI_MCP_CONTENT_SCOPE)
    # stable unique order
    seen: set[str] = set()
    out: list[str] = []
    for p in granted:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return " ".join(out)
