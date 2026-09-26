"""Rewrite MCP tools/list schemas so Gemini Spark can register function calls.

Gemini's function-calling API rejects JSON Schema `$ref` / `$defs` and
`additionalProperties`. Inspector accepts them, so tools work there while Spark
prints the arguments as text and never sends tools/call.
"""

from __future__ import annotations

import copy
import json
import logging
import re
from typing import Any

logger = logging.getLogger("uvicorn.error")

_TOOLS_MARK = re.compile(rb'"tools"\s*:\s*\[')

# Keys Gemini's Schema proto does not accept. Kept: type, description, properties,
# required, items, enum, format, nullable, minimum, maximum, minItems, maxItems,
# minLength, maxLength.
_DROP_SCHEMA_KEYS = frozenset(
    {
        "$defs",
        "$ref",
        "$schema",
        "additionalProperties",
        "default",
        "definitions",
        "title",
        "unevaluatedProperties",
    }
)


def _defs_of(schema: dict[str, Any]) -> dict[str, Any]:
    raw = schema.get("$defs") or schema.get("definitions") or {}
    return raw if isinstance(raw, dict) else {}


def _inline_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Inline `$ref` and drop keys Gemini rejects. Does not mutate `schema`."""
    defs = _defs_of(schema)

    def walk(node: Any, seen: frozenset[str]) -> Any:
        if isinstance(node, list):
            return [walk(item, seen) for item in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            ref = node.get("$ref")
            key = ref.rsplit("/", 1)[-1] if isinstance(ref, str) else ""
            extras = {k: v for k, v in node.items() if k != "$ref"}
            if key and key in defs and key not in seen:
                resolved = copy.deepcopy(defs[key])
                if isinstance(resolved, dict):
                    resolved.update(extras)
                return walk(resolved, seen | {key})
            return walk(extras, seen)
        return {
            k: walk(v, seen)
            for k, v in node.items()
            if k not in _DROP_SCHEMA_KEYS
        }

    walked = walk(schema, frozenset())
    return walked if isinstance(walked, dict) else {}


def _clean_tool_entry(tool: dict[str, Any]) -> bool:
    changed = False
    for key in ("_meta", "title", "outputSchema", "annotations"):
        if key in tool:
            tool.pop(key)
            changed = True
    schema = tool.get("inputSchema")
    if isinstance(schema, dict):
        cleaned = _inline_schema(schema)
        if cleaned != schema:
            tool["inputSchema"] = cleaned
            changed = True
    return changed


def _clean_tools_in_json(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    result = obj.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
        return False
    changed = False
    for tool in result["tools"]:
        if isinstance(tool, dict) and _clean_tool_entry(tool):
            changed = True
    return changed


def _sanitize_json_body(body: bytes) -> bytes:
    if not _TOOLS_MARK.search(body):
        return body
    try:
        obj = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return body
    if _clean_tools_in_json(obj):
        return json.dumps(obj, separators=(",", ":")).encode("utf-8")
    return body


def _sanitize_sse_body(body: bytes) -> bytes:
    if not _TOOLS_MARK.search(body):
        return body
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return body
    if "data:" not in text:
        return _sanitize_json_body(body)
    out_lines: list[str] = []
    changed = False
    for line in text.split("\n"):
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload:
                try:
                    obj = json.loads(payload)
                    if _clean_tools_in_json(obj):
                        changed = True
                        line = "data: " + json.dumps(obj, separators=(",", ":"))
                except json.JSONDecodeError:
                    pass
        out_lines.append(line)
    if not changed:
        return body
    return "\n".join(out_lines).encode("utf-8")


def _header_name(name: bytes | str) -> str:
    raw = name.decode("latin1") if isinstance(name, (bytes, bytearray)) else name
    return raw.lower()


def _as_bytes(value: bytes | str) -> bytes:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    return value.encode("latin1")


def _with_content_length(message: dict[str, Any], length: int) -> dict[str, Any]:
    """Set Content-Length and drop chunked transfer encoding.

    The homelab edge calls cooking nginx with HTTP/1.0. A rewritten body whose
    Content-Length still matches the original schema is truncated, so Spark
    never parses tools/list.
    """
    headers: list[tuple[bytes, bytes]] = []
    for name, value in message.get("headers") or []:
        if _header_name(name) in ("content-length", "transfer-encoding"):
            continue
        headers.append((_as_bytes(name), _as_bytes(value)))
    headers.append((b"content-length", str(length).encode("ascii")))
    return {**message, "headers": headers}


def _content_type(message: dict[str, Any] | None) -> str:
    if not message:
        return "-"
    for name, value in message.get("headers") or []:
        if _header_name(name) == "content-type":
            return _as_bytes(value).decode("latin1", "replace")
    return "-"


class SanitizeToolsListMiddleware:
    """Pure ASGI: Gemini-safe tools/list bodies, with a matching Content-Length.

    Only POST responses are buffered. GET SSE stays a live stream.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return

        start_message: dict[str, Any] | None = None
        buffered = bytearray()
        sent = False

        async def send_wrapper(message):
            nonlocal start_message, sent
            if message.get("type") == "http.response.start":
                start_message = message
                return
            if message.get("type") != "http.response.body":
                await send(message)
                return
            buffered.extend(message.get("body") or b"")
            if message.get("more_body", False):
                return

            original = bytes(buffered)
            cleaned = _sanitize_sse_body(original)
            start = start_message or {
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            }
            sanitized = cleaned != original
            # Always set the length. Streamable HTTP answers POST with SSE and
            # no Content-Length; the homelab edge is HTTP/1.0 and would otherwise
            # buffer or truncate that body.
            start = _with_content_length(start, len(cleaned))
            logger.info(
                "MCP POST finalized status=%s bytes=%s content-type=%s sanitized=%s",
                start.get("status", "-"),
                len(cleaned),
                _content_type(start),
                sanitized,
            )
            await send(start)
            await send(
                {"type": "http.response.body", "body": cleaned, "more_body": False}
            )
            sent = True
            start_message = None

        await self.app(scope, receive, send_wrapper)
        if not sent and start_message is not None:
            await send(start_message)
            await send({"type": "http.response.body", "body": b"", "more_body": False})
