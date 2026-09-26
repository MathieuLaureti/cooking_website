# Delivery: Repo quality standards (#2–#10)

## Status
merged

## Links
- Issues: [#2](https://github.com/MathieuLaureti/cooking_website/issues/2)–[#10](https://github.com/MathieuLaureti/cooking_website/issues/10)
- Input: `docs/input/2026-09-26-repo-quality-standards.md`
- Branch: `feature/repo-quality-2-10`

## Summary

Adds API integration tests, CI server job with Postgres, operations CI matrix and manual smoke checklist, NullPool test DB mode, and documents test coverage in `api.md`.

## Testing

- `docker exec -e DISABLE_IMPORT_WORKER=1 -e SQLALCHEMY_POOL_NULL=1 -e JWT_SECRET=pytest-jwt-secret cw_server_dev pytest -q /code/tests` — **14 passed**

## GitHub

Closes #2, #3, #4, #5, #6, #7, #8, #9, #10
