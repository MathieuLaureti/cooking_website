# Cooking website

Personal cooking console: ingredient pairings, recipe catalog, admin import flows — React UI, FastAPI, Postgres, nginx. See **[documentation hub](docs/README.md)** for features, API, and operations.

## Quick start

```bash
cp .env.example .env   # edit secrets
docker compose up -d --build
```

Console dev: see [console/README.md](console/README.md).

**Server tests:** `cd server && pytest` (see [docs/operations.md](docs/operations.md#server-tests)).

## Agent workflow

This repo uses the **Orchestrator** stack (ideas → GitHub issues → planner loop). Overview: [docs/agents-system.md](docs/agents-system.md). Subagents: `.cursor/agents/`.
