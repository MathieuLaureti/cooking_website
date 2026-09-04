# Architecture

## Runtime map

Browser → nginx (`:81` dev / `:80` prod) → console (Vite/React) or FastAPI server → Postgres (external host) / Redis (`cache`) / Ollama (optional, recipe URL scrape).

Prod is updated by a self-hosted GitHub Actions runner on push to `master` (see [operations.md](operations.md#continuous-deployment-prod)).

```
browser
  └─ nginx
       ├─ /          → console :6665  (dev proxy) or static dist (prod)
       └─ /api/      → server  :6666  (prefix stripped)
            ├─ Postgres  (DB_HOST, cooking_dev | cooking_main)
            ├─ Redis     (redis://cache:6379/0)
            └─ Ollama    (OLLAMA_URL, recipe scrape only)
```

## Responsibilities

- **console**: Vite + React UI. Match checker and recipe manager. Talks only to `/api/...`.
- **server**: FastAPI. Routers, SQLAlchemy async, Alembic, Playwright scrape + Ollama JSON extract, Redis cache-aside for some recipe reads.
- **nginx**: Single public port. Static UI (prod) or reverse-proxy to the Vite container (dev). Strips `/api` and forwards to the server.
- **cache**: Redis 7.4, LRU, no persistence. Recipe list/detail cache only.
- **Postgres**: Source of truth for dishes, recipes, and match-checker seed data. Not a compose service; host is `DB_HOST`.

## Request flow

1. UI `axios` call to `/api/match_checker/...` or `/api/recipes/...`.
2. nginx `location ^~ /api/` → `http://server:6666/` (dev: `nginx/default.dev.conf`; prod: `nginx/default.conf`). In the Vite container, `console/vite.config.ts` also rewrites `/api` when the console is hit directly.
3. FastAPI router in `server/app/router/match_checker.py` or `server/app/router/recipes.py`.
4. Async SQLAlchemy session (`server/app/database.py`) and, for some recipe GETs, Redis (`server/app/cache.py`). URL import uses Playwright then Ollama (`server/app/scripts/APRWS.py`).

## Boundaries

- Console does not talk to Postgres, Redis, or Ollama.
- Server does not serve the React app.
- Nginx does not interpret JSON; it only routes.
- Match-checker data is read-only over HTTP (no create/update/delete routes).
- There is no auth on any route.
