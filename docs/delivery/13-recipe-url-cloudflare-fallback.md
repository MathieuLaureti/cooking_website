# Delivery: Recipe URL import Cloudflare reader fallback

## Status
merged

## Links
- Issue(s): [#13](https://github.com/MathieuLaureti/cooking_website/issues/13)
- Input doc: `docs/input/2026-09-26-recipe-url-cloudflare-fallback.md`
- Branch: `feature/13-recipe-url-cloudflare-fallback`
- PR: https://github.com/MathieuLaureti/cooking_website/pull/14

## Summary

Recipe URL extraction retries through the Jina reader proxy when Playwright only sees a Cloudflare (or similar) bot wall, so imports from sites like Sally's Baking Addiction succeed instead of failing with "Extracted text too short."

## Changes

### UI
- None

### API / backend
- `RecipeExtractor._fetch_text` in `server/app/scripts/extract.py`: Playwright wait tweak, bot-wall detection, `r.jina.ai` fallback via httpx.

### Data / config / migrations
- None

### Evergreen docs
- `docs/features/recipe-import.md`
- `docs/decisions/2026-09-25-gemini-recipe-extract.md`

## Testing

### Automated
- Commands: `docker exec -e DISABLE_IMPORT_WORKER=1 -e JWT_SECRET=pytest-jwt-secret cw_server_dev pytest -v /code/tests/test_extract_page_text.py`
- Result: **pass** (unit tests for bot-wall / minimum text helpers)
- Commands: `docker exec cw_server_dev python -c "..."` — `_fetch_text` on Sally's URL returns >10k chars with ingredients (**pass**, manual script in dev container)

### Manual
- Re-queue failed URL import in admin after deploy; confirm status `ready` with extract JSON.

## GitHub

### PR title
`[import] Fallback when Playwright hits Cloudflare on recipe URLs (#13)`

### PR body
```markdown
## Summary
- Detect Cloudflare-style bot walls and short Playwright body text during recipe URL import.
- Fall back to Jina reader (`r.jina.ai`) before calling Gemini.
- Document behavior in recipe-import and Gemini extract decision docs.

Closes #13

## Testing
- `pytest -v /code/tests/test_extract_page_text.py` in `cw_server_dev`
- Verified `_fetch_text` on Sally's salted caramel URL in dev container
```

### Issue comment
Shipped on branch `feature/13-recipe-url-cloudflare-fallback`; see PR when open.
