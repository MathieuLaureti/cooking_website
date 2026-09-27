# Operations

## Dev

`docker compose` using `docker-compose.yml` (project name `cooking_dev`).

| Service | Container | Image / build | Host access |
|---------|-----------|---------------|-------------|
| nginx | `cw_nginx_dev` | `nginx:1.29.3-alpine` | `localhost:81` → container `:80` |
| console | `cw_console_dev` | `./console` Dockerfile | Vite `:6665` (via nginx `/`) |
| server | `cw_server_dev` | `./server` Dockerfile target `dev` | FastAPI `:6666` (via nginx `/api/`) |
| cache | `cw_redis_dev` | `redis:7.4-alpine` | internal `cache:6379` |

- Server and console bind-mount source (`./server:/code`, `./console:/app`). Uvicorn `--reload`.
- Nginx config: `nginx/default.dev.conf` (proxies `/` to `console:6665`).
- `DB_NAME` forced to `cooking_dev`.

## Prod

`docker compose -f docker-compose.prod.yml` (project name `cooking_prod`).

- Nginx **builds** the console (`nginx/Dockerfile`) and serves `dist` with `nginx/default.conf`. No console container. Host `:80`. The Vite prod build sets asset URLs under `/recipes/` for the public site path; local dev (`docker-compose.yml`) still serves the app at `/`.
- Server image target `prod` (gunicorn + uvicorn workers). `DB_NAME=cooking_main`.
- Healthcheck: `GET http://127.0.0.1:6666/health` inside the server container.
- Gunicorn writes HTTP access lines to stdout (`--access-logfile -` in prod Dockerfile).
- No source bind mounts.

### Prod login / API debugging

Admin login uses `ADMIN_USERNAME` / `ADMIN_PASSWORD` in `.env`; [`seed_admin`](../server/app/seed_admin.py) syncs them into Postgres on each server container start.

| Symptom | Likely cause |
|---------|----------------|
| `cw_nginx_prod` log `POST /api/auth/login` **401** | Request reached FastAPI; wrong username/password in the POST body (not a routing issue). |
| No `cw_server_prod` log line | Normal before access logging; nginx 401 still means the app responded. After deploy, server stdout should show `POST /auth/login`. |
| Browser Network URL is `/api/…` at domain root | Stale UI bundle or wrong path; public API must be **`/recipes/api/…`**. |
| `curl` OK, browser fails | Hard refresh; confirm Network payload matches `.env` (`admin` + `ADMIN_PASSWORD`). |

Checks on the cooking host:

```bash
curl -s -w "\nHTTP %{http_code}\n" -X POST http://localhost/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"…","password":"…"}'

curl -s -w "\nHTTP %{http_code}\n" -X POST https://www.homelabdu204.ca/recipes/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"…","password":"…"}'
```

Both should return **200** when credentials match `.env`. Re-sync admin: `docker compose -f docker-compose.prod.yml up -d --force-recreate server`.

## Environment

From `.env.example` (do not commit real `.env` values):

| Var | Used by |
|-----|---------|
| `DB_USER` | server / Alembic / wait-for-db |
| `DB_PASSWORD` | same |
| `DB_HOST` | default `192.168.2.99`; compose also sets this |
| `DB_PORT` | default `5432` |
| `GEMINI_API_KEY` | server-side key for recipe URL and image import |
| `GEMINI_MODEL` | Gemini model id; default `gemma-4-31b-it` |
| `JWT_SECRET` | JWT signing + registration code HMAC (required in prod) |
| `JWT_EXPIRE_MINUTES` | Token TTL; default `10080` (7 days) |
| `ADMIN_USERNAME` | Bootstrap first admin when `user` table is empty |
| `ADMIN_PASSWORD` | Bootstrap password for first admin |
| `MCP_API_KEY` | Optional shared secret for CLI/Cursor IDE MCP (see [features/mcp.md](features/mcp.md)). Grok Bot prefers OAuth. |
| `PUBLIC_BASE_URL` | Public site prefix for OAuth metadata and MCP discovery. Prod: `https://www.homelabdu204.ca/recipes`. Dev: `http://localhost:81` |
| `MCP_OAUTH_CLIENT_ID` / `MCP_OAUTH_CLIENT_SECRET` | Optional pre-registered OAuth client (Gemini “Advanced features”); synced on server start via `seed_oauth_client` |
| `MCP_OAUTH_EXTRA_REDIRECT_URIS` | Optional comma-separated extra OAuth redirect URIs (e.g. grok.com DCR callbacks not in the built-in Gemini / Cursor lists) |
| `MCP_OAUTH_ACCESS_EXPIRE_SECONDS` | MCP OAuth access token TTL (default `3600`) |
| `MCP_OAUTH_REFRESH_EXPIRE_SECONDS` | Refresh token TTL in Redis (default `2592000`) |

Recreate the **server** container after changing MCP/OAuth env vars. Rebuild **nginx** after nginx config changes or **console** changes (static UI + PWA manifest/service worker). Prod MCP URL: `https://<domain>/recipes/mcp/`. Mobile install: [features/mobile-pwa.md](features/mobile-pwa.md).

## MCP Inspector (debug)

Run on a machine with **Node 22.19+** (Inspector engine; Node 20 may warn) and route to the MCP URL (your laptop for prod homelab). Uses `MCP_API_KEY` + `PUBLIC_BASE_URL` from `.env`:

```bash
chmod +x scripts/mcp-inspector.sh   # once
./scripts/mcp-inspector.sh          # web UI
./scripts/mcp-inspector.sh probe    # HEAD, OAuth metadata, initialize, tools/list, ping
```

Details: [tools/mcp-inspector/README.md](../tools/mcp-inspector/README.md). This does **not** replace Gemini Spark OAuth testing.

## Edge nginx (homelab)

Gemini Spark uses long-lived **Streamable HTTP** (SSE-style) on `GET /recipes/mcp/`. The cooking-site container nginx already disables buffering for MCP; the **first hop** (443 VPN host and any `/recipes/` proxy) must match or the handshake can stall at 60s.

On the homelab host that terminates TLS and proxies to `192.168.2.99` or the Pi, use at least for `/recipes/` (or a dedicated `location` for `/recipes/mcp/`):

```nginx
proxy_buffering off;
proxy_cache off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;
proxy_http_version 1.1;
proxy_set_header Connection "";
```

After changing edge config, reload nginx and start a **new Spark chat** (tool list is cached per session). See [features/mcp.md](features/mcp.md#spark-checklist-transport-schema-cache).

**Grok Bot OAuth discovery** probes RFC 8414 path-segment metadata at the **domain root** before `/recipes/…`. Without this, clients may fall back to `/recipes/.well-known/openid-configuration` and fail OpenID Connect validation. On the TLS host, proxy the path-segment URL to the cooking stack (same JSON as `GET /recipes/.well-known/oauth-authorization-server`):

```nginx
location = /.well-known/oauth-authorization-server/recipes {
    proxy_pass http://192.168.2.99:80/.well-known/oauth-authorization-server;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

Replace `192.168.2.99` with the cooking host if different. Reload edge nginx, then verify:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" \
  https://www.homelabdu204.ca/.well-known/oauth-authorization-server/recipes
```

Expect **200**. The app does **not** serve `/.well-known/openid-configuration` (avoids invalid OIDC stubs); use `oauth-authorization-server` only.

`DATABASE_URL` is optional in `server/app/database.py`; if unset, the URL is built from the `DB_*` vars. Driver is `postgresql+asyncpg`. Redis URL is hardcoded `redis://cache:6379/0`.

## Schema and seed

On every server start, `server/wait-for-db.sh` waits for Postgres, runs `alembic upgrade head`, then runs `python -m app.seed_admin`, `python -m app.seed_oauth_client`, `python -m app.sqlitetopostgres`, then `python -m app.seed_cnf` (before gunicorn workers start). Admin credentials sync from `ADMIN_USERNAME` / `ADMIN_PASSWORD`. Match-checker import reads `server/db.sqlite3` and **skips if `match_checker` already has rows**. CNF import reads `server/seed/cnf/` (food name, food group, nutrient name, nutrient amount) and **skips if any `catalog_food` row has `source = cnf`**. Amounts are stored per 100 g. The files are Health Canada’s Canadian Nutrient File 2026 under the Open Government Licence — Canada; see `server/seed/cnf/SOURCE.md`.

| Environment | Postgres DB | SQLite source | CNF CSVs |
|-------------|-------------|---------------|----------|
| Dev | `cooking_dev` | Bind mount `./server:/code` → `/code/db.sqlite3` | Same mount → `/code/seed/cnf` |
| Prod | `cooking_main` | Baked into server image at build time (`COPY db.sqlite3` in [`server/Dockerfile`](../server/Dockerfile)) | Baked in via `COPY seed/cnf` |

Manual re-import (only if the table was cleared or you need to retry before auto-seed is deployed):

```bash
# Dev
docker compose exec server python -m app.sqlitetopostgres
docker compose exec server python -m app.seed_cnf

# Prod (if SQLite not yet in the image — copy then exec)
docker cp server/db.sqlite3 cw_server_prod:/code/db.sqlite3
docker compose -f docker-compose.prod.yml exec server python -m app.sqlitetopostgres
docker compose -f docker-compose.prod.yml exec server python -m app.seed_cnf
```

Prod image builds require `server/db.sqlite3` on the build host (gitignored; not in git). The CNF CSVs are in the repo and are copied into the image.

## Ingredient search prototype

`server/scripts/ollama_run.py` resolves one ingredient name to one CNF food, or prints a miss. The matcher itself is `server/app/ingredient_match.py`, which the admin screen also calls through `POST /api/alias_reviews/match`. It reads `catalog_alias` first. When that misses, it calls Laya (`http://192.168.2.99:11435/api/decide`) only on foods whose names contain the query words. Confidence of at least `0.75` inserts `catalog_alias` for the typed string. Below that, it upserts `catalog_alias_review`. On a terminal, the script then asks for a number. Enter leaves the row for the admin screen. The dev server image bind-mounts `./server`, so the script is `/code/scripts/ollama_run.py` there. The prod image does not copy `server/scripts/`; the admin field still works because the matcher is in `app/`.

```bash
docker compose exec server python scripts/ollama_run.py "beurre salé"
```

See [Ingredient identity](decisions/2026-09-25-ingredient-identity.md#prototype).

## Recipe URL queue

The server process starts one loop (`server/app/recipe_import_worker.py`) that claims `recipe_url_import` rows one at a time. It does not need a separate container. A restart sets leftover `running` rows back to `queued`.

The Chrome extension is unpacked from `extension/`. In Chrome, open `chrome://extensions`, turn on Developer mode, and choose **Load unpacked** on that folder. The options page signs in with an admin account against the site base (default `https://www.homelabdu204.ca/recipes`). The popup sends the active tab to `POST /api/recipe_imports` and does not wait for Gemini. See [Recipe URL queue](features/recipe-import.md).

## Server tests

Pytest lives under `server/tests/`. The import worker is off during tests (`DISABLE_IMPORT_WORKER=1` in `tests/conftest.py`).

| Check | Command |
|-------|---------|
| All tests | From repo root: `cd server && pytest` |
| Unit only (no Postgres) | `cd server && pytest -m "not integration"` |
| Integration (DB) | Postgres reachable via `.env` `DB_*` or `TEST_DATABASE_URL` / `DATABASE_URL`; then `cd server && pytest -m integration` |

Integration tests run `alembic upgrade head` once per session against that database. Use a dedicated test database name (for example `cooking_test`) when pointing at a shared Postgres host so dev data is not mixed with test migrations.

Pytest sets `SQLALCHEMY_POOL_NULL=1` (see `server/tests/conftest.py`) so async SQLAlchemy does not reuse connections across event loops.

Install deps: same as the server image (`pip install -r server/requirements.txt`). In dev you can run inside the server container:

```bash
docker compose exec server pytest
```

## Manual browser smoke (optional)

Homelab or local dev with stack up (`docker compose`, port `81`):

1. Open `http://localhost:81`, log in as admin.
2. Tap the yellow **admin** control, confirm registration code and alias queue load.
3. Tap **user**, confirm pairings/recipes load.
4. Optional: install PWA from the install affordance ([mobile PWA](features/mobile-pwa.md)).

Automated Playwright in CI is deferred; use this checklist before prod deploy when UI changed.

## Continuous integration

Pushes and pull requests run [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) on GitHub-hosted runners:

| Job | Working dir | Steps |
|-----|-------------|--------|
| **console** | `console/` | `npm ci`, `npm run lint`, `npm run build` |
| **server** | `server/` | Postgres 16 service, `pip install`, `alembic upgrade head`, `pytest -v` |

Fix failing jobs before merging to `master`. Server job uses env `DB_*` pointing at the CI Postgres service and `DISABLE_IMPORT_WORKER=1`.

## Continuous deployment (prod)

Prod redeploys automatically when `master` is pushed to GitHub. A self-hosted GitHub Actions runner on this host runs [`.github/workflows/deploy-prod.yml`](../.github/workflows/deploy-prod.yml), which calls [`scripts/deploy-prod.sh`](../scripts/deploy-prod.sh).

### One-time runner setup

Run on this host (requires `gh` authenticated and Docker without sudo):

```bash
./scripts/setup-actions-runner.sh
```

This downloads the ARM64 runner to `~/actions-runner`, registers it with label `prod`, and installs the systemd service. Alternatively: GitHub → repo **Settings → Actions → Runners → New self-hosted runner** (Linux ARM64).

### What deploy does

1. `git fetch origin master` and `git reset --hard origin/master` in `/home/mlaureti/cooking_website`
2. Fail if `.env` is missing (secrets stay local, not in git)
3. `docker compose -f docker-compose.prod.yml build`
4. `docker compose -f docker-compose.prod.yml up -d --remove-orphans`
5. Smoke check: `GET http://localhost/api/health` (up to ~2.5 min)

Alembic runs on server container start via `wait-for-db.sh`; no separate migration step in the deploy script.

### Triggers

| Trigger | When |
|---------|------|
| Push to `master` | Automatic deploy after the push |
| **Actions → Deploy prod → Run workflow** | Manual redeploy (`workflow_dispatch`) |

Dev (`docker-compose.yml`, port `81`) is not restarted by this workflow. Dev bind mounts pick up the same `git reset` on the next file access.

### Rollback

```bash
cd /home/mlaureti/cooking_website
git reset --hard <previous-sha>
./scripts/deploy-prod.sh
```

Or reset locally and use **Run workflow** in GitHub Actions.

### Expectations

- Prod image rebuild on ARM can take several minutes (React build + Playwright server image).
- Brief API/nginx interruption while containers are recreated; prod nginx waits for the server healthcheck before starting.
