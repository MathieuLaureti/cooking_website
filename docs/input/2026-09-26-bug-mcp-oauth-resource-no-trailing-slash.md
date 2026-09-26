# MCP OAuth resource URL must not have trailing slash

## Status
ready-for-github

## Change type
bugfix

## Problem
Grok Bot cloud connector compares the MCP server URL to OAuth protected-resource metadata exactly. Metadata returned `"resource": "…/recipes/mcp/"` while the connector uses `…/recipes/mcp` (no slash), so sign-in never starts. Cursor desktop is more lenient.

## Expected
`GET /.well-known/oauth-protected-resource` → `"resource": "https://www.homelabdu204.ca/recipes/mcp"` (no trailing slash). `/mcp` and `/mcp/` both reach the MCP endpoint (no redirect).

## Scope
- `mcp_resource_url()` in `server/app/mcp_oauth_config.py`
- Docs + unit test

## Note
Fix was briefly live on prod via manual `docker compose` before this slice; merge + CD will reconcile.
