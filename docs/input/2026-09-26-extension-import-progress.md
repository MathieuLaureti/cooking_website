# Chrome extension: import in-progress indication

## Status
ready-for-github

## Change type
feature

## Gates
- Gate 1+2: client requested 2026-09-26 — “lets add a small ui indication”.

## Summary
While a URL is queued or extracting, show status in the extension popup (current tab) and a toolbar badge with the number of active imports.

## Acceptance
- Popup polls `GET /api/recipe_imports` (admin token) and shows state for the active tab URL.
- Badge shows count of `queued` + `running` rows; clears when none.
- Documented in `docs/features/recipe-import.md`.
