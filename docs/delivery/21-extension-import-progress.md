# Delivery: Extension import in-progress UI

## Status
pr-open

## Links
- Issue(s): [#21](https://github.com/MathieuLaureti/cooking_website/issues/21)
- Input doc: `docs/input/2026-09-26-extension-import-progress.md`
- Branch: `feature/21-extension-import-progress`
- PR: https://github.com/MathieuLaureti/cooking_website/pull/22

## Summary

The Chrome extension shows queue/extract state for the current tab in the popup and a toolbar badge with the number of active imports.

## Changes

### UI
- `extension/` — `import-status.js`, `background.js`, popup polling, badge.

### API / backend
- None (uses existing `GET /api/recipe_imports`).

### Evergreen docs
- `docs/features/recipe-import.md`

## Testing

### Automated
- **not run** (extension; manual only)

### Manual
- Reload unpacked extension → queue a slow URL → popup shows **Extracting recipe…**; badge shows `1` → when ready, popup shows **Ready — review in admin**; badge clears.

## GitHub — PR
### Title
Extension: show URL import in progress (#21)

### Body
```markdown
## Summary
- Popup polls import queue and shows status for the current tab.
- Toolbar badge shows count of queued/running imports.

Closes #21

## Test plan
- [ ] Reload extension in Chrome, queue a recipe URL, confirm popup + badge
```
