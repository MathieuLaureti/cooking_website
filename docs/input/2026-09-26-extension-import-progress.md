# Admin: URL import in-progress indication

## Status
ready-for-github

## Change type
feature

## Gates
- Gate 1+2: client requested 2026-09-26; clarified **admin app** (not Chrome extension).

## Summary
On the admin **URL imports** panel, show clearly when extraction is running or queued (URL + status), not only a count.

## Acceptance
- In-progress block for `running` and `queued` rows with visible “extracting” state.
- Empty state only when nothing is active and nothing to review.
- `docs/features/admin.md` updated.
