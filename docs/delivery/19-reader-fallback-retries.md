# Delivery: Jina reader fallback retries for URL import

## Status
pr-open

## Links
- Issue(s): [#19](https://github.com/MathieuLaureti/cooking_website/issues/19)
- Input doc: `docs/input/2026-09-26-reader-fallback-retries.md`
- Branch: `fix/19-reader-fallback-retries`
- PR: **pending**

## Summary

URL import is more reliable on Cloudflare-heavy sites: the Jina reader fallback retries up to three times with backoff, and failure messages include both Playwright and reader errors.

## Changes

### UI
- None

### API / backend
- `server/app/scripts/extract.py` — `_fetch_reader_fallback_with_retries`, `_format_fetch_errors`.

### Data / config / migrations
- None

### Evergreen docs
- `docs/features/recipe-import.md`

## Testing

### Automated
- Commands: `docker exec cw_server_dev pytest -v /code/tests/test_extract_page_text.py`
- Result: **pass** (6 tests)

### Manual
- Retry a previously failed Sally's URL import after deploy; expect `ready` without multiple admin retries.

### Tester sign-off
- Unit tests cover combined errors and reader retry-then-success path.

## GitHub — PR
### Title
Harden Jina reader fallback for URL import (#19)

### Body
```markdown
## Summary
- Retry `r.jina.ai` reader fallback up to 3 times with short backoff when Playwright hits bot walls.
- Include Playwright and reader errors in the final extraction failure message.

Closes #19

## Testing
- `pytest -v /code/tests/test_extract_page_text.py`
```
