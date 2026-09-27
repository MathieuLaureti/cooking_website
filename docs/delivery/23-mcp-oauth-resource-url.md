# Delivery: MCP OAuth protected-resource URL (no trailing slash)

## Status
pr-open

## Links
- Issue(s): #23 — https://github.com/MathieuLaureti/cooking_website/issues/23
- Input doc: docs/input/2026-09-26-mcp-oauth-resource-url.md
- Branch: `fix/23-mcp-oauth-resource-url`
- PR: **pending** (filled after `gh pr create`)

## Summary
OAuth protected-resource metadata now advertises the MCP resource identifier as `…/recipes/mcp` without a trailing slash (RFC 9728 / Gemini Spark). Streamable HTTP clients still connect at `…/recipes/mcp/`.

## Changes
### UI
- None

### API / backend
- `GET /.well-known/oauth-protected-resource` — JSON `resource` from `mcp_resource_url()` without trailing slash.

### Data / config / migrations
- None

### Evergreen docs
- `docs/api.md`, `docs/features/mcp.md`

## Testing
### Automated
- Commands: `docker compose exec -T server python -m pytest tests/test_mcp_oauth_config.py -q`
- Result: 2 passed

### Manual / smoke
- `curl -H 'Cache-Control: no-cache' https://www.homelabdu204.ca/recipes/.well-known/oauth-protected-resource` → `resource` ends with `/mcp`, not `/mcp/`.

## Ship checklist
- [ ] PR reviewed on GitHub
- [ ] CI green (if applicable)
- [ ] Merge approved by client
- [ ] After merge: rebuild `cw_server_prod` from merged `master` (prod may already match pre-merge hotfix)

## GitHub artifacts
### PR title
Fix MCP OAuth protected-resource URL (no trailing slash)

### PR body
```
Fixes #23

## Summary
- `mcp_resource_url()` returns `…/mcp` for RFC 9728 protected-resource metadata.
- Unit test + doc note distinguishing metadata `resource` vs HTTP MCP URL (`…/mcp/`).

## Test plan
- [x] `pytest tests/test_mcp_oauth_config.py`
- [x] curl oauth-protected-resource on prod (no trailing slash on `resource`)
```

### Suggested commit message
```
fix(mcp): OAuth protected-resource URL without trailing slash (#23)
```
