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

1. UI `apiClient` call to `/api/...` with `Authorization: Bearer <token>` (except login/register).
2. nginx `location ^~ /api/` → `http://server:6666/` (dev: `nginx/default.dev.conf`; prod: `nginx/default.conf`).
3. FastAPI router decodes JWT from the Bearer header (`server/app/auth.py`) — no DB hit on authenticated reads.
4. Async SQLAlchemy session for data access; Redis cache on some recipe GETs.

## Boundaries

- Console does not talk to Postgres, Redis, or Ollama.
- Server does not serve the React app.
- Nginx does not interpret JSON; it only routes.
- Match-checker data is read-only over HTTP (no create/update/delete routes).
- **All content routes require a valid JWT.** Only `/health`, `POST /auth/login`, and `POST /auth/register` are public.
- Admin-only routes (recipe mutations, AI import, registration code) check `role == "admin"` from the JWT.
- Registration codes are HMAC-derived from `JWT_SECRET` + minute bucket — no session store or Redis for auth.
