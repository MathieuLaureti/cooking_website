# URL import retry on admin panel

## Status
ready-for-github

## Gates (record)
- **Gate 1** (create GitHub issue): confirmed by client 2026-09-26 — issue [#17](https://github.com/MathieuLaureti/cooking_website/issues/17) (created before formal ask; acknowledged retroactively).
- **Gate 2** (implement): confirmed by client 2026-09-26 — “do what you haven’t done and push”.

## Change type
feature

## Summary
When a queued URL import fails extraction, admins should be able to **Retry** (re-queue the same row) from the URL imports section instead of only **Discard**.

## Motivation
After server fixes (e.g. Cloudflare fallback), a failed import should be retried without re-submitting from the extension or losing the URL.

## Detailed intent
- `POST /api/recipe_imports/{id}/retry` for `failed` rows: set `queued`, clear `error` and `extract`.
- Admin UI: **Retry** beside **Discard** when the visible card is `failed` (no **Keep**; **ready** keeps Keep/Discard).
- Reject retry when another active row exists for the same normalized URL.

## Acceptance
- Failed import in admin shows **Retry** and **Discard**; retry moves row to `queued` and worker picks it up again.
- Ready import unchanged (Keep + Discard).
- Documented in `docs/api.md` and `docs/features/admin.md`.
