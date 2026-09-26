# Reader fallback retries for URL import

## Status
ready-for-github

## Change type
bugfix

## Summary
When Playwright hits a bot wall, Jina reader fallback can succeed but is flaky. Retry the reader a few times and surface both Playwright and reader errors on final failure.

## Gates
- Gate 1 + 2: client approved 2026-09-26 — “don’t worry just do it”.

## Acceptance
- Reader fallback retried up to 3 times with short backoff.
- Final `Web extraction failed` message includes reader detail when reader fails.
- Unit tests for retry/error formatting; docs updated.
