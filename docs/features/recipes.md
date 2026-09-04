# Recipes

## What it does

Catalog of **dishes**, each with one or more **recipes**. A recipe is a list of **components** (named sections), each with ingredients (`name`, `quantity` string, `unit`) and numbered instructions. Recipes can be typed in, edited, deleted, or imported by scraping a URL through Ollama.

## User flow

1. Load dish list; search filters dishes; “+ New Dish” posts a name.
2. Select a dish → list that dish’s recipes; “+ Create Recipe” opens the draft form.
3. Draft form: optional URL scrape, then edit title / components / ingredients / steps and submit (create or edit).
4. Select a recipe → viewer with edit and two-step delete.

## UI

- `console/src/components/RecipeManager.tsx` — dish/recipe search, create dish, wire API.
- `console/src/components/RecipeDraftForm.tsx` — form plus URL and image-upload affordances.
- `console/src/components/RecipeViewer.tsx` — read view, edit, confirm delete.
- Types: `console/src/components/types.ts` (`DishSearch`, `RecipeFull`, …). `API_BASE = '/api/recipes'`.
- Client `Ingredient.quantity` is typed as `number`; the API stores `quantity` as a **string**.

## Backend

- Router: `server/app/router/recipes.py`.
- Models: `Dish`, `Recipe`, `RecipeComponent`, `Ingredient`, `Instruction`.
- Cache-aside (`server/app/cache.py`): `dishes:all`, `dish_recipes:{dish_id}`, `full_recipe:{recipe_id}` (1h). Create-recipe deletes `dish_recipes:{dish_id}` only.
- URL import: `WebRecipeExtractor` in `server/app/scripts/APRWS.py` (Playwright → Ollama JSON → `_create_recipe_in_db`).
- Image import class exists (`server/app/scripts/APRIR.py`) but has **no registered route**.

## Data

See [data model](../data-model.md). Hierarchy: dish → recipe → recipe_component → ingredient / instruction.

## Edge cases

- Duplicate dish name → 400. Duplicate recipe name on the same dish → 400.
- Delete dish is rejected while recipes exist; the console never calls delete-dish or rename-dish.
- Console fetch-one-recipe uses `/recipe/{dishId}/{recipeId}`; server expects `/recipe/{recipe_id}` only.
- Console posts `/recipe_image/{dish_id}`; that endpoint is not implemented (UI shows “AI EXTRACTION ERROR.”).
- URL scrape can take tens of seconds; nginx read timeout is 300s. Failures return 500 with a string `detail`.
- Stale Redis: new dishes may not appear until `dishes:all` expires; edited/deleted recipes can stay in `full_recipe:{id}` for up to an hour.
