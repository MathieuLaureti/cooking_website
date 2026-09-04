# Recipes

## What it does

Catalog of **dishes**, each with one or more **recipes**. A recipe is a list of **components** (named sections), each with ingredients (`name`, `quantity` string, `unit`) and numbered instructions. Requires login. Only **admins** can create, edit, delete, or import via AI.

## User flow

1. Sign in (see [auth](auth.md)).
2. Load dish list; search filters dishes.
3. **Admin only**: “+ New Dish” posts a name; “+ Create Recipe” opens the draft form.
4. Select a dish → list that dish’s recipes.
5. **Admin only**: draft form with optional URL scrape, edit, submit.
6. Select a recipe → viewer. **Admin only**: edit and two-step delete.

## UI

- `console/src/components/RecipeManager.tsx` — dish/recipe search; admin create controls gated by `isAdmin`.
- `console/src/components/RecipeDraftForm.tsx` — form plus URL and image-upload affordances (admin only).
- `console/src/components/RecipeViewer.tsx` — read view; edit/delete hidden for non-admins.
- Types: `console/src/components/types.ts`. API calls via `console/src/api/client.ts` (`API_BASE = '/api/recipes'`).

## Backend

- Router: `server/app/router/recipes.py`.
- GET routes: any authenticated user (`Depends(get_current_user)`).
- POST/PUT/DELETE + `GET /recipe_url`: admin only (`Depends(require_admin)`).
- Cache-aside (`server/app/cache.py`): `dishes:all`, `dish_recipes:{dish_id}`, `full_recipe:{recipe_id}` (1h).
- URL import: `WebRecipeExtractor` in `server/app/scripts/APRWS.py`.

## Data

See [data model](../data-model.md). Hierarchy: dish → recipe → recipe_component → ingredient / instruction.

## Edge cases

- Duplicate dish name → 400. Duplicate recipe name on the same dish → 400.
- Non-admin API writes → 403.
- Console posts `/recipe_image/{dish_id}`; that endpoint is not implemented.
- URL scrape can take tens of seconds; nginx read timeout is 300s.
