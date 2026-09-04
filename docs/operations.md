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

- Nginx **builds** the console (`nginx/Dockerfile`) and serves `dist` with `nginx/default.conf`. No console container. Host `:80`.
- Server image target `prod` (gunicorn + uvicorn workers). `DB_NAME=cooking_main`.
- Healthcheck: `GET http://127.0.0.1:6666/health` inside the server container.
- No source bind mounts.

## Environment

From `.env.example` (do not commit real `.env` values):

| Var | Used by |
|-----|---------|
| `DB_USER` | server / Alembic / wait-for-db |
| `DB_PASSWORD` | same |
| `DB_HOST` | default `192.168.2.99`; compose also sets this |
| `DB_PORT` | default `5432` |
| `OLLAMA_URL` | recipe URL (and unused image) extractors |
| `MODEL_NAME` | present in env; URL extractor currently hardcodes `qwen2.5:7b` |
| `IMAGE_MODEL_NAME` | present in env; image extractor currently hardcodes `llama3.2-vision:11b` |
| `JWT_SECRET` | JWT signing + registration code HMAC (required in prod) |
| `JWT_EXPIRE_MINUTES` | Token TTL; default `10080` (7 days) |
| `ADMIN_USERNAME` | Bootstrap first admin when `user` table is empty |
| `ADMIN_PASSWORD` | Bootstrap password for first admin |

`DATABASE_URL` is optional in `server/app/database.py`; if unset, the URL is built from the `DB_*` vars. Driver is `postgresql+asyncpg`. Redis URL is hardcoded `redis://cache:6379/0`.

## Schema and seed

On every server start, `server/wait-for-db.sh` waits for Postgres then runs `alembic upgrade head`.

Match-checker seed (once, skips if the table is non-empty):

```bash
docker compose exec server python -m app.sqlitetopostgres
```

SQLite file must be at `server/db.sqlite3` (present in the server bind mount in dev).

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
