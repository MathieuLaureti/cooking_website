# Scratch: URL import pipeline UI, AI scheduler, ingredient quality

## Status
exploring (ingredient slice promoted separately)

## Linked input
docs/input/2026-09-27-recipe-ingredient-extraction.md — prompt + JSON-LD only; pipeline UI/scheduler still here

## 2026-09-27 — User intent (/discuss)

### Admin URL import — 3 visible steps

User wants explicit progress in admin (not just "Extracting recipe"):

| Step | Label (UI) | Meaning |
|------|------------|---------|
| 1/3 | Reaching browser | Server loads the URL (Playwright goto + wait, or start of fetch) |
| 2/3 | Retrieving data | Page text captured and deemed usable (Playwright body or Jina reader fallback) |
| 3/3 | Extraction via AI | Gemini `emit_recipe` on cached page text |

Polling every ~3s (existing) can show `step/3` + label from API fields.

### Step memory + 503 (free tier)

- Gemini 503 UNAVAILABLE = transient capacity, not "scrape broken".
- On AI failure after steps 1–2 succeed: **do not re-fetch** the URL; retry **only step 3** on a schedule (~5 min user suggestion).
- Persist captured text (or reference) on the import row so retries are cheap.
- Failed step should surface differently from hard fetch failures (e.g. "Waiting for model" vs "Web extraction failed").

### AI scheduler (general)

- **Priority:** interactive paths first (`GET /api/recipes/recipe_url`, draft chat, image import) over **automated** URL queue worker.
- **Clean scheduler:** single place for Gemini calls — retries, backoff, priority queue, maybe max concurrent background jobs.
- Background jobs defer when user request holds the lock or priority slot.

### Sally's salted caramel — missing ingredients

URL: https://sallysbakingaddiction.com/homemade-salted-caramel-recipe/

Page lists 4 ingredients; extract had 1 structured ingredient but good instructions (butter/cream/salt appear in step text only).

Hypotheses to validate when building:

1. **Prompt/schema:** `_SYSTEM` does not stress "every line under Ingredients" or splitting qty/unit from parenthetical weights.
2. **Page text shape:** Playwright strips nav/header; ingredients block may be lower quality in `innerText` vs visible DOM (WPRM JSON-LD might exist — not used today).
3. **Model behavior:** Multiple titles on page ("Salted Caramel", "Homemade…", "Salted Caramel Sauce"); model may collapse components or stop after first ingredient.
4. **Code gap:** URL `_emit` uses raw `httpx` — **no** `_gemini_post` retry loop (chat path has 503 retries). Transient failures may mark whole job `failed` and admin retries **full** pipeline today.

## Current code reality (as of discuss)

- `recipe_import_worker.process_job` → single `extractor.from_url` (atomic under `_url_lock`).
- `from_url`: `_fetch_text` then `_emit`; no persisted intermediate state on `recipe_url_import`.
- Table fields: `status`, `extract`, `error` only — no `step`, no cached page text.
- Admin UI: "Extracting recipe" + queue list (`AdminHome.tsx`); no sub-steps.
- Retry API: `failed` → `queued` clears error/extract — **full re-run**.

## Design sketches (draft, not decided)

### Pipeline state on row

Option A — extend `status` + JSON `pipeline`:

```yaml
pipeline:
  step: 2          # 1..3
  step_label: Retrieving data
  page_text: "..." # or object storage key if huge
  ai_next_attempt_at: ISO8601
  last_ai_error: "503 ..."
```

Option B — statuses: `fetching`, `extracting_ai`, `ai_deferred` (queued for scheduler), `ready`, `failed`.

UI maps any in-progress to `step/3` label.

### Scheduler

- One `GeminiScheduler` asyncio: priority heap (user=0, background=1).
- `_url_lock` today serializes URL scrape + AI; refactor to: lock scrape only, scheduler for all `_emit`/`chat`/`_gemini_post`.
- Background import when 503: set `ai_deferred`, `next_attempt_at = now + 5m`, release worker to next URL (don't block queue on model).

Open question: block worker on deferred row vs skip to next queued URL.

### Ingredient quality fixes (orthogonal but same PR batch?)

- Stronger system prompt for ingredient completeness.
- Post-validate: if instructions mention common ingredient words but `ingredients.length` suspiciously low → one retry with "list only missing ingredients".
- Optional: parse `application/ld+json` Recipe from HTML before/alongside innerText (deterministic ingredient list).

## Decisions (2026-09-27 follow-up)

### Step 3/3 semantics

**3/3 = last step in progress**, not "job finished." While Gemini is calling or backing off after 503, UI stays **3/3 — Extraction via AI** (optional subline: "retry in …"). **`ready`** / **`failed`** are separate terminal states.

### AI backoff

Use **exponential backoff** for retryable model errors (503, etc.), e.g. 5 min → 10 min → 20 min, then **`failed`** (exact caps TBD at spec time).

### Cached fetch data (Postgres + queue cap)

When step 2 succeeds and step 3 fails or defers, persist **captured page text** on the import row in **Postgres** (same ~40k cap as today’s in-memory slice).

Add a **queue limiter** so extension/admin queue cannot grow unbounded with rows holding large cached text:

- Cap **count** of active imports (`queued`, `running`, deferred-AI states, maybe `ready` awaiting keep).
- Optionally cap **total cached bytes** or reject new `POST /api/recipe_imports` with a clear error when at limit.
- Policy detail TBD (e.g. max N queued + M with cached text).

### Worker vs deferred rows

Still prefer worker **not** blocked on long AI backoff — process other URLs; deferred row shows **3/3** until AI succeeds or exhausts backoff.

## Open questions

- Exact queue limits (N rows? include `ready`? extension vs admin).
- Ingredient quality approach — see chat explanation (user asked for clarity on former Q4).

## Ingredient quality options (for planning)

1. **Prompt only** — tell the model more strictly to copy every ingredient line.
2. **Sanity check + AI retry** — if result has too few ingredients vs page, one extra AI pass.
3. **Structured data from the page** — read hidden `Recipe` JSON in HTML for ingredient list, use AI for the rest.
