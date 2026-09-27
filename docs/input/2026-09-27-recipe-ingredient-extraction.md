# Recipe URL import: complete ingredients (prompt + JSON-LD)

## Status
ready-for-github

## Change type
bugfix

## Summary
Improve recipe URL/image extraction so ingredient lists match the source page: stronger model instructions plus, when the HTML exposes Schema.org `Recipe` JSON-LD, parse `recipeIngredient` and require those items in the structured output.

## Motivation
Imports from sites like Sally's Baking Addiction can return full instructions but only one ingredient while the page lists four. Fetch succeeds; the model under-fills `ingredients`.

## Detailed intent

### 1 — Prompt (all URL/image extracts)
Update the chef system prompt used by `emit_recipe` in `server/app/scripts/extract.py` to require:
- Every line from the page's **Ingredients** section appears in `components[].ingredients`.
- Do not stop after the first ingredient; do not move ingredient lines into instructions only.
- When a separate structured ingredient list is provided in the user message (from JSON-LD), include **all** of those items with quantities/units split when possible.

### 2 — JSON-LD when present (Playwright path only)
During Playwright fetch, **before** stripping `<script>` nodes, collect `application/ld+json` blocks, parse JSON, resolve `@graph` / `@type` `Recipe` (and common variants), read `recipeIngredient` (string or array).
- If at least one ingredient string is found, append to the user payload sent to Gemini (e.g. "Structured recipe metadata (Schema.org):\n- …").
- If no Recipe JSON-LD is found, behavior unchanged except improved prompt.
- **Jina reader fallback** returns markdown, not raw HTML — no JSON-LD on that path; rely on prompt + page text only.

### 3 — Acceptance
- Re-import or extract `https://sallysbakingaddiction.com/homemade-salted-caramel-recipe/` → four ingredients (sugar, butter, heavy cream, salt) with reasonable qty/unit strings.
- Site without JSON-LD still extracts via text-only (no regression).
- Unit tests: JSON-LD parser fixture(s); optional mocked extract asserting prompt includes metadata block.

## Constraints
- No change to admin pipeline UI, Postgres step cache, or Gemini scheduler in this slice (separate input/brainstorm).
- Keep existing `PAGE_CHAR_CAP` and `_url_lock` behavior unless a tiny refactor is required to return `(text, jsonld_ingredients)` from fetch.
- Document behavior in `docs/features/recipes.md` (and recipe-import if fetch path is described).

## Open questions
- None blocking — JSON-LD is best-effort; user accepts it will not work on all sites.

## Risks and criticism
- Duplicate or conflicting ingredients if JSON-LD and page text disagree — prompt should prefer completeness without duplicating same item twice (dedupe by normalized name optional follow-up).
- Some JSON-LD lists combined strings ("1 cup sugar") — model still splits qty/unit; optional server-side split is out of scope unless tests show need.

## Linked scratch
docs/brain-storming/2026-09-27-url-import-pipeline-and-extraction.md

## Technical plan (draft)

1. Add `parse_recipe_jsonld_ingredients(html: str) -> list[str]` (or parse from Playwright `page.content()` before DOM strip) in `extract.py` or small helper module.
2. Change `_fetch_text_playwright` to return text plus optional ingredient strings; thread through `from_url` into `_emit` user parts.
3. Extend `_SYSTEM` as above.
4. Tests in `server/tests/` for JSON-LD samples (inline HTML fixture).
5. Docs sync per plan-docs.

## Proposed issues (draft)
- Single issue: **Fix incomplete ingredient extraction on URL import (prompt + Schema.org JSON-LD)**
