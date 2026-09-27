# Delivery: URL import pipeline resilience (#31)

## Status
merged

## Issue
- https://github.com/MathieuLaureti/cooking_website/issues/31

## Branch
- `feature/31-url-import-pipeline-resilience`

## Summary
Resumable URL import pipeline with admin step labels, Postgres page cache, Gemini 503 backoff, queue cap, and priority scheduler.

## PR
- https://github.com/MathieuLaureti/cooking_website/pull/32

## Test plan
- [ ] CI pytest
- [ ] Admin UI shows 1/3–3/3 during import
- [ ] Simulate 503 → `ai_wait` without losing page text
