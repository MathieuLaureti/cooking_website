# MCP OAuth: protected-resource URL without trailing slash

## Status
ready-for-github

## Change type
bugfix

## Summary
Gemini Spark (and other RFC 9728 clients) expect the `resource` field in `GET /.well-known/oauth-protected-resource` to match the canonical MCP resource identifier **without** a trailing slash. Production was advertising `https://www.homelabdu204.ca/recipes/mcp/` while clients need `…/recipes/mcp`.

## Motivation
OAuth linking for Gemini Spark MCP failed because protected-resource metadata did not match the resource identifier the client validates. HTTP Streamable MCP transport URL for clients remains `…/mcp/` (trailing slash); only the OAuth metadata `resource` value changes.

## Detailed intent

### Repro
1. `curl -H 'Cache-Control: no-cache' https://www.homelabdu204.ca/recipes/.well-known/oauth-protected-resource`
2. Observe `"resource":"https://www.homelabdu204.ca/recipes/mcp/"` (trailing slash).

### Expected
`"resource":"https://www.homelabdu204.ca/recipes/mcp"` (no trailing slash).

### Root cause
`server/app/mcp_oauth_config.py` — `mcp_resource_url()` returned `f"{public_base_url()}/mcp/"`. `PUBLIC_BASE_URL` was already correct; not an env misconfiguration.

### Implementation (draft — applied locally, not on a delivery branch/PR yet)
- Change `mcp_resource_url()` to `…/mcp` (no slash).
- Unit test `server/tests/test_mcp_oauth_config.py`.
- Docs: `docs/api.md`, `docs/features/mcp.md` (distinguish metadata `resource` vs client MCP URL).

### Process note
Agent implemented and rebuilt **prod** (`docker-compose.prod.yml` / `cw_server_prod`) **before** Issue + PR gates. Production may already reflect the fix; git/PR must still land via pipeline.

## Constraints
- Separate from open slice **#21** / PR **#22** (extension import progress).
- Branch target: `fix/mcp-oauth-resource-url` (or similar) off default branch after gate 2.

## Open questions
- None for scope.

## Risks and criticism
- **Pipeline deviation:** hot deploy without enrolled issue; uncommitted changes currently on `feature/21-extension-import-progress` — must not merge with PR #22.
- Token `aud` remains `mcp`; no JWT change expected.

## Out of scope
- Homelab edge nginx version mismatch (1.18 vs 1.24) unless linking still fails after metadata fix.
- grok.com connectors vs Grok Bot.

## Technical plan (draft)
1. Enroll single `agent-managed` issue; manifest `delivery_mode: single`.
2. Branch from `main` (or rebase fix commits onto `fix/…`).
3. Coder: ensure code + tests + docs match above.
4. Tester: pytest `test_mcp_oauth_config.py`; `scripts/mcp-inspector.sh probe` OAuth metadata check.
5. Documenter: PR `Fixes #n`, delivery report, ship checklist.

## Proposed issues (draft)
1. **Fix OAuth protected-resource `resource` URL (no trailing slash)** — bugfix, Gemini Spark MCP OAuth.

## Raw notes
- Live verification after hot rebuild: metadata returns `…/recipes/mcp` without slash.
- `cw_server_dev` was misleading during diagnosis; public traffic uses prod stack on port 80.
