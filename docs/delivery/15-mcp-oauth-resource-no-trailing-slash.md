# Delivery: #15 MCP OAuth resource URL without trailing slash

## Issue
https://github.com/MathieuLaureti/cooking_website/issues/15

## PR
https://github.com/MathieuLaureti/cooking_website/pull/16

## What shipped (in PR)
- `mcp_resource_url()` returns `…/mcp` without trailing slash.
- `.cursor/rules/code-change-pipeline.mdc` blocks pre-PR prod deploy.
- Docs + `test_mcp_oauth_config.py`.

## Off-pipeline note
Prod was rebuilt once via manual `docker compose -f docker-compose.prod.yml` before this PR. After merge, self-hosted CD runs `scripts/deploy-prod.sh` from `origin/master`.

## Ship proposal
- [ ] Approve merge of PR #16 on GitHub.
- [ ] Confirm Deploy prod workflow / health check passes.
