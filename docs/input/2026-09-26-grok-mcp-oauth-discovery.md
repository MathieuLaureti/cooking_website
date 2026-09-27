# Grok Bot MCP OAuth discovery (root well-known + OIDC stub)

## Status
ready-for-github

## Change type
bugfix

## Summary
Grok Bot fails OAuth discovery for the cooking MCP server because domain-root RFC 8414 path-segment URLs return 404 on homelab edge nginx, and the connector then uses `/recipes/.well-known/openid-configuration`, which is validated as full OpenID Connect and lacks required fields.

## Motivation
Grok Bot sign-in progresses past the trailing-slash fix but stops at “finding your login server.” The connector must obtain plain OAuth 2.0 authorization server metadata without being forced through invalid OIDC validation.

## Detailed intent
1. **Homelab edge nginx (manual / out of repo):** Serve `GET /.well-known/oauth-authorization-server/recipes` on `www.homelabdu204.ca` by proxying to the cooking host’s `/.well-known/oauth-authorization-server` (after `/recipes/` strip on the app path, the upstream is `http://<cooking-host>:80/.well-known/oauth-authorization-server`).
2. **In repo (cooking_website):** Document the edge `location` block in `docs/operations.md` (and cross-link from `docs/features/mcp.md`).
3. **In repo (optional hardening):** Remove or stop advertising `GET /.well-known/openid-configuration` on the FastAPI app so clients that probe `/recipes/.well-known/openid-configuration` do not receive OAuth AS JSON at an OIDC URL (fallback if edge cannot be changed immediately). Verify Gemini Spark still discovers via `oauth-authorization-server` and `oauth-protected-resource`.

## Constraints
- Edge TLS nginx is not in this repository; deploy on the homelab VPN/TLS host.
- Do not break existing Gemini Spark OAuth (re-link + new chat smoke after deploy).
- Follow plan-docs for API/feature doc updates if app routes change.

## Open questions
- Exact cooking host IP/hostname on edge proxy (prod: `192.168.2.99:80` per architecture).

## Risks and criticism
- Removing `openid-configuration` may affect clients that insist on OIDC discovery only; mitigated by keeping `oauth-authorization-server` and documenting edge path-segment URL.
- Two-track fix (edge + app) requires coordinating edge reload with app deploy for fastest Grok unblock.

## Acceptance criteria (preview)
- `curl -sS -o /dev/null -w "%{http_code}" https://www.homelabdu204.ca/.well-known/oauth-authorization-server/recipes` → **200** (after edge change).
- `curl -sS https://www.homelabdu204.ca/recipes/.well-known/oauth-authorization-server` → unchanged valid OAuth AS JSON.
- Grok Bot can complete OAuth and reach MCP tools (user verification).
- Gemini Spark OAuth smoke still passes protected-resource + authorize path (tester).

## Gate 1
User confirmed **yes** in agent chat 2026-09-26 (Grok MCP OAuth discovery).
