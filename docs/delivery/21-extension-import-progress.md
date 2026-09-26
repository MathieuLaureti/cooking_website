# Delivery: Admin URL import in-progress UI

## Status
pr-open

## Links
- Issue(s): [#21](https://github.com/MathieuLaureti/cooking_website/issues/21)
- Input doc: `docs/input/2026-09-26-extension-import-progress.md`
- Branch: `feature/21-extension-import-progress`
- PR: https://github.com/MathieuLaureti/cooking_website/pull/22

## Summary

Admin **URL imports** shows an in-progress section (extracting + queue) so you can see when the worker is busy while Gemini runs.

## Changes

### UI
- `console/src/components/AdminHome.tsx` — in-progress block, header **N in progress** / **idle**.

### API / backend
- None

### Evergreen docs
- `docs/features/admin.md`

## Testing

### Automated
- CI console build (on PR)

### Manual
- Queue a URL from the extension → admin shows **Extracting recipe** with URL; when done, **Keep** card appears.

## GitHub — PR
### Title
Admin: show URL import in progress (#21)

### Body
```markdown
## Summary
- Admin URL imports panel shows active extraction and queued URLs with a clear in-progress state.

Closes #21

## Test plan
- [ ] Queue import → admin shows extracting block until ready
```
