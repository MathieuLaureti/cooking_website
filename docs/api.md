# API

No authentication. JSON unless noted.

Browser origin hits nginx `/api/`, which proxies to FastAPI with `/api` stripped.

Example: UI `/api/match_checker/ingredients` → server `/match_checker/ingredients`.

Pydantic shapes: `server/app/pydantic_models/match_checker.py`, `server/app/pydantic_models/recipes.py`.

## Health

### `GET /api/health`

- Purpose: liveness (prod compose healthcheck hits `http://127.0.0.1:6666/health` inside the server container).
- Request: none
- Response: `"Hello World"` (JSON string)
- Code: `server/app/main.py`

## Match checker

Code: `server/app/router/match_checker.py`. Prefix `/match_checker`.

### `GET /api/match_checker/ingredients`

- Purpose: list all pairing entries for the search dropdown.
- Request: none
- Response: `[{ "id": int, "title": string }, ...]`
- Errors: none beyond 5xx

### `GET /api/match_checker/ingredient/{id}`

- Purpose: full pairing record for one ingredient.
- Request: path `id` (int)
- Response:

```json
{
  "id": 1,
  "title": "ACHIOTE SEEDS",
  "avoid": ["..."],
  "affinities": ["achiote + pork + sour orange"],
  "matches": [["chicken", 1], ["pork", 2]]
}
```

- Errors: `404` `{ "detail": "Ingredient not found" }`

## Recipes — dishes

Code: `server/app/router/recipes.py`. Prefix `/recipes`.

### `GET /api/recipes/dishes`

- Purpose: list dishes.
- Request: none
- Response: `[{ "id": int, "name": string }, ...]`
- Cache: Redis key `dishes:all`, TTL 3600s. Not invalidated on create/edit/delete dish.
- Errors: none beyond 5xx

### `POST /api/recipes/dish`

- Purpose: create a dish.
- Request body: `{ "name": string }`
- Response: `{ "id": int, "name": string }`
- Errors: `400` if that name already exists

### `PUT /api/recipes/dish_edit/{dish_id}`

- Purpose: rename a dish.
- Request: path `dish_id`; body `{ "name": string }`
- Response: `{ "id": int, "name": string }`
- Errors: `404` `"Dish not found"`
- Notes: console does not call this.

### `DELETE /api/recipes/dish/{dish_id}`

- Purpose: delete a dish with no recipes.
- Request: path `dish_id`
- Response: `{ "detail": "Dish deleted successfully" }`
- Errors: `404` `"Dish not found"`; `400` if any recipe still references the dish
- Notes: console does not call this.

## Recipes — recipes

Full recipe object (`RecipeFull`):

```json
{
  "id": 1,
  "name": "string",
  "dish_id": 1,
  "components": [
    {
      "name": "string",
      "instructions": [{ "step": 1, "text": "string" }],
      "ingredients": [{ "name": "string", "quantity": "string", "unit": "string" }]
    }
  ]
}
```

Create body (`RecipeCreate`) is the same without `id` (still includes `dish_id` and `name`).

### `GET /api/recipes/recipes/{dish_id}`

- Purpose: list recipes for one dish.
- Request: path `dish_id`
- Response: `[{ "id": int, "name": string }, ...]` (empty list if the dish has none; no 404)
- Cache: `dish_recipes:{dish_id}`, TTL 3600s. Invalidated on manual/URL create only.

### `GET /api/recipes/recipe/{recipe_id}`

- Purpose: full recipe tree.
- Request: path `recipe_id`
- Response: `RecipeFull`
- Cache: `full_recipe:{recipe_id}`, TTL 3600s. Not invalidated on edit/delete.
- Errors: `404` `"Recipe not found"`
- Notes: console currently requests `/api/recipes/recipe/{dish_id}/{recipe_id}`, which does not match this route.

### `POST /api/recipes/recipe/{dish_id}`

- Purpose: create a recipe under a dish (manual form).
- Request: path `dish_id`; body `RecipeCreate`
- Response: `RecipeFull`
- Errors: `404` if dish missing; `400` if a recipe with the same name already exists on that dish
- Side effects: invalidates `dish_recipes:{dish_id}`

### `PUT /api/recipes/recipe_edit/{recipe_id}`

- Purpose: replace name and rebuild all components (clears existing components, then inserts the payload’s).
- Request: path `recipe_id`; body `RecipeFull`
- Response: `RecipeFull`
- Errors: `404` `"Recipe not found"`

### `DELETE /api/recipes/recipe/{recipe_id}`

- Purpose: delete a recipe (ORM cascade removes components, ingredients, instructions).
- Request: path `recipe_id`
- Response: `{ "detail": "Recipe deleted successfully" }`
- Errors: `404` `"Recipe not found"`

### `GET /api/recipes/recipe_url/{dish_id}?url=`

- Purpose: scrape a web page, ask Ollama for `RecipeCreate` JSON, then persist like manual create.
- Request: path `dish_id`; query `url` (required)
- Response: `RecipeFull`
- Errors: `404`/`400` from create; `500` with `detail` string on scrape/LLM failure
- Timeouts: Playwright page load 60s; Ollama HTTP 120s; nginx proxy read 300s
- Notes: extractor is constructed with hardcoded model `qwen2.5:7b`, not `MODEL_NAME`.

There is **no** `POST /api/recipes/recipe_image/{dish_id}` on the server. `ImageRecipeExtractor` exists in `server/app/scripts/APRIR.py` and the console posts to that path; the router never registers it.
