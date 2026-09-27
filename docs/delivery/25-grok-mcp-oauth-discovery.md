# Delivery: #25 Grok MCP OAuth discovery

- Issue: https://github.com/MathieuLaureti/cooking_website/issues/25
- Input doc: docs/input/2026-09-26-grok-mcp-oauth-discovery.md
- Branch: `fix/25-grok-mcp-oauth-discovery`

## Summary

Document homelab edge proxy for RFC 8414 path-segment OAuth AS metadata (`/.well-known/oauth-authorization-server/recipes`). Remove the in-app `openid-configuration` route so Grok does not validate plain OAuth JSON as OpenID Connect.

## Changes

- `server/app/router/mcp_oauth.py` — drop `GET /.well-known/openid-configuration`.
- `server/tests/test_mcp_oauth_discovery.py` — AS metadata 200; openid-configuration 404.
- `docs/operations.md`, `docs/features/mcp.md`, `docs/api.md` — edge `location` + discovery URLs.

## Tester

- Commands: `cd server && pytest tests/test_mcp_oauth_discovery.py -q`
- Manual (after edge reload): `curl -sS -o /dev/null -w "%{http_code}\n" https://www.homelabdu204.ca/.well-known/oauth-authorization-server/recipes` → **200**
- Manual: `curl -sS -o /dev/null -w "%{http_code}\n" https://www.homelabdu204.ca/recipes/.well-known/openid-configuration` → **404** (post-deploy)
- User: Grok Bot OAuth reconnect

## Status

open

## Ship checklist

- [ ] CI green on PR
- [ ] Merge after user ship approval
- [ ] Edge nginx reloaded on homelab TLS host (operator, not CD)
- [ ] `pytest tests/test_mcp_oauth_discovery.py`
- [ ] Grok retry confirmed by user
