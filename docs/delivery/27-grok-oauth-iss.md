# Delivery: Grok OAuth RFC 9207 iss

- Issue: https://github.com/MathieuLaureti/cooking_website/issues/27
- Input: docs/input/2026-09-27-grok-oauth-iss.md

## Summary
Advertise `authorization_response_iss_parameter_supported` and return `iss` on the OAuth authorize redirect so Cursor/Grok completes the code → token exchange.

## Changes
- `server/app/router/mcp_oauth.py` — metadata flag, `iss` on redirect, `resource` on authorize/token
- `server/app/mcp_oauth_store.py` — persist `resource` on auth codes
- Tests: discovery metadata + full authorize → token flow

## Verification
- `pytest server/tests/test_mcp_oauth_discovery.py server/tests/test_mcp_oauth_authorize.py`
- After prod deploy: Grok OAuth; `docker compose -f docker-compose.prod.yml logs -f server` should show `POST /oauth/token` after authorize 302
