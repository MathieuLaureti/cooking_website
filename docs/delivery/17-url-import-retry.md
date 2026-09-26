# Delivery: Admin retry for failed URL imports

## Status
merged

## Links
- Issue(s): [#17](https://github.com/MathieuLaureti/cooking_website/issues/17)
- Input doc: `docs/input/2026-09-26-url-import-retry.md`
- Branch: `feature/17-url-import-retry`
- PR: https://github.com/MathieuLaureti/cooking_website/pull/18

## Summary

Admins can **Retry** a failed extension URL import from the admin panel. The server re-queues the same `recipe_url_import` row so extraction runs again after fixes, without discarding the URL or re-submitting from the extension.

## Changes

### UI
- `console/src/components/AdminHome.tsx` — **Retry** on failed cards (no extract); **Keep**/**Discard** unchanged for **ready**.

### API / backend
- `POST /api/recipe_imports/{import_id}/retry` (admin): `failed` → `queued`, clears `error` and `extract`; `400` if not failed or another active row exists for the same normalized URL.

### Data / config / migrations
- None

### Evergreen docs
- `docs/api.md`
- `docs/features/admin.md`
- `docs/features/recipe-import.md`

## Testing

### Automated
- Commands: `docker exec cw_server_dev pytest -v /code/tests/test_recipe_import.py`
- Result: **pass** (2 tests)
- CI on PR #18: **pass** (console + server workflows)

### Manual
- Admin → URL imports: failed row shows error, **Retry**, **Discard**; **Retry** increments extracting count and row eventually becomes **ready** or **failed** again.
- Result: **not run** (awaiting deploy to homelab after merge)

### Tester sign-off
- Integration tests for retry success and conflict with an already-active URL; CI green on branch.

## Screenshots / recordings
- N/A

## Risks / follow-ups
- Failed rows stay behind the oldest **ready** card until that row is kept or discarded (existing queue UX).

## GitHub — commit (for Orchestrator or explicit user request)
### Subject
Add retry for failed URL imports in admin queue.

### Body
Closes #17

## GitHub — PR
### Title
Admin: retry failed URL imports

### Body
```markdown
## Summary
- Adds `POST /api/recipe_imports/{id}/retry` to re-queue failed imports (clears error/extract).
- Admin **URL imports** shows **Retry** next to **Discard** on failed cards; **ready** cards unchanged (**Keep** + **Discard**).
- Integration tests and docs updated.

Closes #17

## Test plan
- [x] `pytest -v /code/tests/test_recipe_import.py` in `cw_server_dev`
- [x] CI (console + server)
- [ ] On admin, failed import → **Retry** → re-extract after deploy
```

### Issue comment
Gate 1 (issue #17) and gate 2 (implement on `feature/17-url-import-retry`) confirmed by client after retroactive review. PR #18 open for ship validation; CI and local pytest pass.

## Ship checklist (client approval required before merge)
1. Review PR #18
2. Approve merge on GitHub (or reply with approved checklist items)
3. Deploy server + console on homelab
4. Retry the previously failed URL import in admin
