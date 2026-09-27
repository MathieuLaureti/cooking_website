# URL import: resumable pipeline, admin steps, AI scheduler

## Status
ready-for-github

## Change type
feature

## Summary
Split URL import into three resumable steps with admin UI (1/3–3/3), persist captured page text in Postgres when fetch succeeds, retry only Gemini on 503 with exponential backoff, cap queue size, and route all Gemini calls through a priority scheduler (interactive before background worker).

## Motivation
Free-tier Gemini returns transient 503; today the whole import fails and **Retry** re-scrapes. Admins cannot see fetch vs AI progress. Background imports should not block interactive URL import on the draft form.

## Detailed intent

### Pipeline steps (API + admin UI)
Expose `pipeline_step` (1–3) and `pipeline_label` on each import row while in progress:

| Step | Label |
|------|--------|
| 1 | Reaching browser |
| 2 | Retrieving data |
| 3 | Extraction via AI |

**3/3 means step 3 in progress** (including AI backoff), not complete. Terminal: `ready`, `failed`.

Admin polls `GET /api/recipe_imports` (existing interval); show `N/3 Label` on running / waiting rows.

### Resumable state (Postgres)
Add columns on `recipe_url_import` (Alembic):

- `page_text` (Text, nullable) — capped at 40_000 chars when saved
- `structured_ingredients` (JSONB, nullable) — JSON-LD lines from fetch, for AI retry without re-scrape
- `pipeline_step` (small int, nullable)
- `ai_attempt_count` (int, default 0)
- `ai_next_attempt_at` (timestamptz, nullable)

New status **`ai_wait`**: fetch done, Gemini deferred (503/backoff). Row stays at **3/3** with optional `error` or subline showing next retry time.

Worker must **not** block the queue during backoff; pick other `queued` rows. Re-run step 3 when `ai_next_attempt_at <= now()`.

Admin **Retry** on `failed`: if `page_text` still present, skip to step 3; else full pipeline from step 1.

### AI backoff
Retryable Gemini errors (503, 429, etc.): exponential delay **5 min → 10 min → 20 min** (`ai_attempt_count`), then `failed`. Do not clear `page_text` on retryable failure.

Wire URL `_emit` through shared **`_gemini_post`** (or scheduler) like chat.

### Queue limiter
Defaults (env-tunable):

- `RECIPE_IMPORT_MAX_ACTIVE=25` — count rows in `queued`, `running`, `ai_wait`, `ready`
- `POST /api/recipe_imports` returns **409** with clear message when at cap
- Extension behavior unchanged except error text

### Gemini scheduler
New module (e.g. `app/gemini_scheduler.py`):

- Priority: **interactive** (`GET recipe_url`, `POST recipe_image`, `POST recipe_chat`) before **background** (import worker)
- Single retry/backoff policy for API calls
- Scrape lock separate from model queue (`_url_lock` only around browser fetch)

### Docs
Update `docs/features/recipe-import.md`, `docs/features/admin.md`, `docs/data-model.md`, `docs/api.md` as needed.

## Out of scope
- Ingredient prompt + JSON-LD (shipped #29 / PR #30)

## Constraints
- One agent-managed issue, one PR (`/automatic` expedited path — scope is large but delivered as single batch).

## Linked scratch
docs/brain-storming/2026-09-27-url-import-pipeline-and-extraction.md

## Technical plan (draft)

1. Alembic migration + model fields; extend `RecipeImportItem`.
2. Refactor `RecipeExtractor`: `fetch_for_import()` vs `emit_from_cached()`; worker state machine in `recipe_import_worker.py`.
3. `gemini_scheduler` + migrate `_emit`, `chat`, worker AI path.
4. `recipe_import.py`: queue cap on POST; `_item` includes step fields; adjust ACTIVE statuses and unique index if needed for `ai_wait`.
5. `AdminHome.tsx`: step display + ai_wait copy.
6. Tests: worker states, cap, backoff classification, API shape.

## Proposed issues (draft)
- Single issue: **URL import resumable pipeline, admin steps, and Gemini scheduler**
