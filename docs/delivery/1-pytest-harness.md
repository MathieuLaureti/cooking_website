# Delivery: Server pytest harness and Postgres fixtures

## Status
merged

## Links
- Issue(s): [#1](https://github.com/MathieuLaureti/cooking_website/issues/1)
- Input doc: `docs/input/2026-09-26-repo-quality-standards.md`
- Branch: `feature/1-pytest-harness`
- PR: https://github.com/MathieuLaureti/cooking_website/pull/11

## Summary

Adds a `server/tests/` pytest layout with async HTTP client and optional Postgres integration fixtures, disables the recipe import worker during tests, and documents how to run tests locally and in the dev container.

## Changes

### UI
- None

### API / backend
- `DISABLE_IMPORT_WORKER` env skips background import worker in app lifespan (test-friendly).

### Data / config / migrations
- None

### Evergreen docs
- `docs/operations.md` — Server tests section
- `README.md` — pointer to server tests

## Testing

### Automated
- Commands: `docker exec -e DISABLE_IMPORT_WORKER=1 -e JWT_SECRET=pytest-jwt-secret cw_server_dev pytest -v /code/tests`
- Result: **pass** (2 passed: `test_health`, `test_db_session_select_one`)

### Manual
- **not run** (covered by container run above)

## GitHub

### PR title
`[testing] Add server pytest harness and Postgres fixtures (#1)`

### PR body
```markdown
## Summary
Pytest harness under `server/tests/` with async client fixture and integration DB session (alembic upgrade + `SELECT 1`). Import worker disabled when `DISABLE_IMPORT_WORKER=1`.

## Testing
- `docker compose exec server pytest` (after image rebuild picks up `pytest-asyncio`)

Closes #1
```

## Ship checklist
- [ ] Push branch
- [ ] Open PR
- [ ] Merge after review
- [ ] Move manifest primary issue to #2
