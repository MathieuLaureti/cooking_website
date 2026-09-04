---
name: plan-docs
description: >-
  Keep living app documentation in docs/ current whenever code changes. Use when
  in Plan Mode, implementing a feature, editing endpoints, models, UI, Docker,
  nginx, or env, fixing bugs that change behavior, or when the user asks to
  plan or document a change. After any such edit, update docs/ in the same turn.
---

# Keep docs in sync

`docs/` must describe the app **as it is after this change**. Plan Mode drafts the markdown; Agent mode writes it. Implementation without a plan still patches `docs/` in the **same turn** as the code.

## When this applies

- Plan Mode, or any plan / spec / design
- Any edit to routers, pydantic/DB models, Alembic, console UI, compose, nginx, Dockerfiles, env, or seed scripts
- User asks to document the app

Skip only a pure refactor with no behavior, API, schema, UI, or ops change — say so in the reply.

## Hard rules

1. Read `docs/README.md` and the files in the map below before editing them.
2. **Same turn as the code.** Do not finish with “docs can be updated later.”
3. Present tense. No changelog voice. No invented APIs/tables/services; use `TODO` plus what to inspect if unknown.
4. Browser paths use the `/api/...` prefix. Link to code paths (`server/app/router/recipes.py`).
5. If implementation drifted from the plan, patch docs before finishing.

## Change → doc map

| If you change | Update |
|---------------|--------|
| `server/app/router/**`, `server/app/pydantic_models/**` | `docs/api.md` + matching `docs/features/*.md` |
| `server/app/db_models/**`, `server/alembic/**` | `docs/data-model.md` |
| `docker-compose*.yml`, `nginx/**`, `**/Dockerfile*`, `.env.example`, `server/wait-for-db.sh`, `server/app/database.py`, `server/app/cache.py` | `docs/architecture.md`, `docs/operations.md` |
| `console/src/**` | matching `docs/features/*.md` |
| `server/app/sqlitetopostgres.py`, `server/db.sqlite3` | `docs/data-model.md` (Legacy / seed), `docs/operations.md` |

New user-facing capability → new `docs/features/<name>.md` and a link in `docs/README.md`. Removed capability → delete or shrink that feature doc and the index link.

## Docs tree

```
docs/
  README.md
  architecture.md
  data-model.md
  api.md
  operations.md
  features/<feature>.md
  decisions/YYYY-MM-DD-<slug>.md
```

Current surfaces: console (match checker + recipe manager); server FastAPI (`/match_checker`, `/recipes`, `/health`); nginx `/` → UI, `/api/` → server (strip `/api`); Postgres `cooking_dev` / `cooking_main`; Redis `cache`; compose `docker-compose.yml` + `docker-compose.prod.yml`.

## Agent workflow (code changes)

1. Make the code change.
2. Patch every matching doc from the map so it matches the new code (add/rename/remove endpoints, columns, env vars, user flows).
3. Do not mark the task done until those files are saved.

## Plan workflow

Complete this in the plan, with **full markdown** (not a sketch) for every file that will change:

```
Docs impact:
- [ ] architecture.md
- [ ] data-model.md
- [ ] api.md
- [ ] operations.md
- [ ] features/<name>.md (create / update / delete)
- [ ] decisions/<date>-<slug>.md (only if a real tradeoff)
- [ ] docs/README.md index
```

First implementation todo: write those `docs/` files, then code. If the code drifts, patch docs again.

## Update vs create

- Prefer editing an existing file
- New feature doc only for a distinct user-facing capability
- New ADR only for a real tradeoff (storage, caching, auth, deploy topology, sync vs async)
- Keep `docs/README.md` links in sync

## Quality bar

A new engineer can run the stack and find the right code from docs alone.

- **API**: method, `/api/...` path, request/response, errors, auth if any
- **Data model**: SQLAlchemy / Alembic, not a hoped-for schema
- **Features**: user flow + components and routers
- **Operations**: compose file, env vars, migration/seed commands

Section headings: [templates.md](templates.md)
