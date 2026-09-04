# Doc templates

Use these section headings. Drop a section only if it would be empty. Fill from code, not from memory.

## `docs/README.md`

```markdown
# Cooking website docs

Short what / why. Link the files below with one-line descriptions.

## Features
- [Match checker](features/match-checker.md)
- [Recipes](features/recipes.md)

## System
- [Architecture](architecture.md)
- [Data model](data-model.md)
- [API](api.md)
- [Operations](operations.md)

## Decisions
- Link ADRs in `decisions/`
```

## `docs/architecture.md`

```markdown
# Architecture

## Runtime map
Who talks to whom: browser → nginx → console / server → Postgres / Redis / Ollama.

## Responsibilities
- console:
- server:
- nginx:
- cache:
- Postgres:

## Request flow
1. UI call
2. nginx location
3. FastAPI router
4. DB / cache / external

## Boundaries
What each service must not own.
```

## `docs/data-model.md`

```markdown
# Data model

Postgres. Source of truth: `server/app/db_models/models.py` and `server/alembic/versions/`.

## Tables
### `<table>`
- columns (name, type, constraints)
- relationships
- notes (indexes, JSON vs array, uniqueness)

## Legacy / seed
SQLite `server/db.sqlite3` (`api_ingredient` → `match_checker`) and `app/sqlitetopostgres.py`.
```

## `docs/api.md`

```markdown
# API

Browser origin hits nginx `/api/`, which proxies to FastAPI with `/api` stripped.
Example: UI `/api/match_checker/ingredients` → server `/match_checker/ingredients`.

## `<router prefix>`
### `METHOD /api/...`
- Purpose
- Request (query / body)
- Response
- Errors
- Code: `server/app/router/<file>.py`
```

## `docs/operations.md`

```markdown
# Operations

## Dev
`docker compose` / `docker-compose.yml`. Ports, service names, volume mounts.

## Prod
`docker-compose.prod.yml`. Differences from dev.

## Environment
Vars from `.env.example` and what they do. Never paste secrets.

## Schema and seed
- `alembic upgrade head` (runs from `wait-for-db.sh`)
- SQLite → Postgres: `docker compose exec server python -m app.sqlitetopostgres`
```

## `docs/features/<feature>.md`

```markdown
# <Feature name>

## What it does
## User flow
## UI
Components and important client types (`console/src/...`).
## Backend
Routers, models, cache, extractors.
## Data
Tables / JSON shapes.
## Edge cases
Empty, not found, validation, long-running jobs.
```

## `docs/decisions/YYYY-MM-DD-<slug>.md`

```markdown
# <Decision title>

Date: YYYY-MM-DD

## Context
## Options considered
## Decision
## Consequences
```

Write an ADR only when the plan picked among real alternatives.
