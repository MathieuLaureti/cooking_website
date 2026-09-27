# Delivery: Recipe ingredient extraction (prompt + JSON-LD)

## Status
open

## Issue
- https://github.com/MathieuLaureti/cooking_website/issues/29

## Input
- `docs/input/2026-09-27-recipe-ingredient-extraction.md`

## Branch
- `fix/29-recipe-ingredient-extraction`

## Summary
URL import sends complete ingredient lists: stronger `emit_recipe` system prompt plus Schema.org `recipeIngredient` parsed from Playwright HTML when present.

## Changes
- `server/app/scripts/extract.py` — JSON-LD parser, `PageFetchResult`, prompt text
- `server/tests/test_recipe_jsonld.py`, `test_extract_page_text.py`
- `docs/features/recipes.md`, `docs/features/recipe-import.md`

## Test plan
- [ ] `pytest server/tests/test_recipe_jsonld.py server/tests/test_extract_page_text.py`
- [ ] Retry Sally's URL import after deploy; four ingredients in extract

## PR
- TBD
