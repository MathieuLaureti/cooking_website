# API

JWT Bearer authentication on all routes except `/health`, `POST /auth/login`, and `POST /auth/register`.

Send `Authorization: Bearer <token>` on every authenticated request. Token payload includes `sub` (user id), `username`, `role`, `exp`. Protected routes decode the JWT only — no per-request database lookup.

Pydantic shapes: `server/app/pydantic_models/auth.py`, `server/app/pydantic_models/match_checker.py`, `server/app/pydantic_models/nutrition.py`, `server/app/pydantic_models/alias_review.py`, `server/app/pydantic_models/recipe_import.py`, `server/app/pydantic_models/recipes.py`.

Integration coverage for auth, alias review, nutrition, MCP API-key checks, and the recipe import worker lives in `server/tests/` (see [operations](operations.md#server-tests)).

## Health

### `GET /api/health`

- Purpose: liveness (prod compose healthcheck hits `http://127.0.0.1:6666/health` inside the server container).
- Auth: none
- Response: `"Hello World"` (JSON string)
- Code: `server/app/main.py`

## Auth

Code: `server/app/router/auth.py`. Prefix `/auth`.

### `POST /api/auth/login`

- Purpose: authenticate and receive a JWT.
- Auth: none
- Request body: `{ "username": string, "password": string }`
- Response: `{ "access_token": string, "token_type": "bearer", "username": string, "role": "admin" | "user" }`
- Errors: `401` `"Invalid username or password"`

### `POST /api/auth/register`

- Purpose: create a read-only `user` account with a valid registration code.
- Auth: none
- Request body: `{ "username": string, "password": string (min 6), "code": string (7 digits) }`
- Response `201`: `{ "username": string, "role": "user" }`
- Errors: `400` invalid/expired code; `400` username already taken

### `GET /api/auth/me`

- Purpose: return current user from JWT (no DB).
- Auth: Bearer
- Response: `{ "username": string, "role": "admin" | "user" }`
- Errors: `401` missing or invalid token

### `GET /api/auth/registration-code`

- Purpose: current 7-digit registration code for inviting new users.
- Auth: Bearer, admin only
- Response: `{ "code": string, "expires_in_seconds": int }`
- Errors: `401`, `403` `"Admin access required"`

## Match checker

Code: `server/app/router/match_checker.py`. Prefix `/match_checker`. **Auth: Bearer (any role).**

### `GET /api/match_checker/ingredients`

- Purpose: list all pairing entries for the search dropdown.
- Response: `[{ "id": int, "title": string }, ...]`

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

## Nutrition catalog

Code: `server/app/router/nutrition.py`. Prefix `/nutrition`. **Auth: Bearer (any role).** Shapes: `server/app/pydantic_models/nutrition.py`. Data is the Canadian Nutrient File (`source = cnf`). Amounts are per 100 g.

### `GET /api/nutrition/foods`

- Purpose: one window of catalog foods for the nutrition panel. Does not return the full catalog.
- Query: `q` (string, max 80, optional) and `offset` (int, default 0).
- Response: `{ "items": [{ "id": int, "name_en": string, "name_fr": string, "group_en": string | null }, ...], "offset": int, "has_more": bool }`. `items` has at most 50 rows.
- Empty `q` browses every CNF food ordered by `name_en`. A non-empty `q` matches a case-insensitive substring of `name_en` or `name_fr`, or an accent-folded official alias. Whole-word matches come first, then other substring matches, each group ordered by `name_en`. A whole word is the full name or a space-separated token, so `butter` ranks above `buttermilk`.

### `GET /api/nutrition/foods/{food_id}`

- Purpose: one food and every stored nutrient amount.
- Response: the short fields plus `group_fr` and `nutrients`: `[{ "code", "symbol", "name_en", "name_fr", "unit", "decimals", "amount_per_100g" }, ...]`.
- Errors: `404` `{ "detail": "Food not found" }`

## Alias review

Code: `server/app/router/alias_review.py`. Prefix `/alias_reviews`. **Auth: admin.** Shapes: `server/app/pydantic_models/alias_review.py`. Writes go through `server/app/alias_link.py`.

### `POST /api/alias_reviews/match`

- Purpose: run the ingredient matcher on one typed name. An exact alias or a Laya choice of at least `0.75` saves `catalog_alias` and returns `match`. A lower score upserts `catalog_alias_review` and returns `queued`. No catalog food returns `none`.
- Request body: `{ "query": string }` (max 255)
- Response: `{ "status": "match" | "queued" | "none", "confidence": number | null, "match": { "id": int, "name_en": string, "name_fr": string, "group_en": string } | null }`
- Errors: `400` empty or too long; `502` when Laya rejects the call; `403` for a non-admin
- Code: `server/app/ingredient_match.py`

### `GET /api/alias_reviews`

- Purpose: pending names the matcher could not auto-accept.
- Response: `[{ "id": int, "query": string, "confidence": number | null, "candidates": [{ "food_id": int, "name_en": string, "name_fr": string, "probability": number | null }] }, ...]` ordered by `id`.
- Errors: `403` for a non-admin.

### `POST /api/alias_reviews/{review_id}/accept`

- Purpose: link `query` to one candidate food and mark the row resolved.
- Request body: `{ "food_id": int }`
- Response: the same review item, now resolved.
- Errors: `404` when the row is missing or not pending; `400` when `food_id` is not one of `candidates`; `403` for a non-admin.

## Recipes — dishes

Code: `server/app/router/recipes.py`. Prefix `/recipes`.

### `GET /api/recipes/dishes`

- Auth: Bearer (any role)
- Purpose: list dishes.
- Response: `[{ "id": int, "name": string }, ...]` sorted by `name` (case-sensitive DB order).
- Cache: Redis key `dishes:all`, TTL 3600s.

### `POST /api/recipes/dish`

- Auth: **admin**
- Purpose: create a dish.
- Request body: `{ "name": string }`
- Response: `{ "id": int, "name": string }`
- Errors: `400` duplicate name; `401`/`403`
- Cache: deletes `dishes:all`

### `PUT /api/recipes/dish_edit/{dish_id}`

- Auth: **admin**
- Purpose: rename a dish.
- Errors: `404` `"Dish not found"`; `401`/`403`
- Cache: deletes `dishes:all`

### `DELETE /api/recipes/dish/{dish_id}`

- Auth: **admin**
- Purpose: delete a dish with no recipes.
- Errors: `404`, `400` if recipes exist; `401`/`403`
- Cache: deletes `dishes:all` and `dish_recipes:{dish_id}`

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

### `GET /api/recipes/recipes/{dish_id}`

- Auth: Bearer (any role)
- Response: `[{ "id": int, "name": string }, ...]` sorted by `name`.
- Cache: `dish_recipes:{dish_id}`, TTL 3600s.

### `GET /api/recipes/recipe/{recipe_id}`

- Auth: Bearer (any role)
- Response: `RecipeFull`
- Cache: `full_recipe:{recipe_id}`, TTL 3600s.
- Errors: `404` `"Recipe not found"`

### `POST /api/recipes/recipe/{dish_id}`

- Auth: **admin**
- Purpose: manual create on an existing dish. Path `dish_id` wins over any dish field in the body.
- Request body: `{ "name": string, "components": [Component, ...] }`
- Response: `RecipeFull`
- Errors: `404` unknown dish, `400` duplicate recipe name; `401`/`403`
- Cache: deletes `dish_recipes:{dish_id}`

### `POST /api/recipes/recipe`

- Auth: **admin**
- Purpose: manual create when no dish is open. `dish_id` in the body, when set, selects that dish. Otherwise `dish_name` is matched to an existing dish (case-insensitive, accents ignored) or inserted.
- Request body: `{ "name": string, "dish_name": string, "components": [Component, ...] }`
- Response: `RecipeFull`
- Errors: `400` missing dish name or duplicate recipe name, `404` when `dish_id` is set and missing; `401`/`403`
- Cache: deletes `dish_recipes:{dish_id}`, and `dishes:all` when a dish was created

### `PUT /api/recipes/recipe_edit/{recipe_id}`

- Auth: **admin**
- Purpose: replace name and rebuild all components.
- Errors: `404`; `401`/`403`
- Cache: deletes `full_recipe:{recipe_id}` and `dish_recipes:{dish_id}`

### `DELETE /api/recipes/recipe/{recipe_id}`

- Auth: **admin**
- Errors: `404`; `401`/`403`
- Cache: deletes `full_recipe:{recipe_id}` and `dish_recipes:{dish_id}`

### `POST /api/recipes/recipe_chat`

- Auth: **admin**
- Purpose: chat with the Gemini model to build or refine a recipe. The model gets the dish list with ids (or the current dish) and the current draft, so it can attach to an existing dish or propose a new one. It returns a conversational reply and zero or more recipe versions via the `emit_recipes` function call.
- Request body: `{ "message": string, "dish_id": int|null, "history": [{ "role": "user"|"model", "text": string }], "current_recipe": RecipeExtract|null }`
- Response: `{ "reply": string, "recipes": [RecipeExtract, ...] }`
- Errors: `500` on model failure (including a missing `GEMINI_API_KEY`); `401`/`403`
- Code: `server/app/scripts/extract.py` (`RecipeExtractor.chat`)

### `GET /api/recipes/recipe_url?url=&dish_id=`

- Auth: **admin**
- Purpose: scrape `url` with Playwright, extract a recipe with Gemini, then persist. The draft form waits on this call. Optional `dish_id` forces that dish. With no `dish_id`, the model returns `dish_name` and the server matches or creates the dish. This is not the batch queue.
- Response: `RecipeFull`
- Errors: `500` on scrape or model failure (including a missing `GEMINI_API_KEY`); `400`/`404` from dish and recipe checks; `401`/`403`
- Code: `server/app/scripts/extract.py`

## Recipe URL queue

Code: `server/app/router/recipe_import.py`. Prefix `/recipe_imports`. **Auth: admin.** The server process runs one worker (`server/app/recipe_import_worker.py`) that scrapes the oldest `queued` row, then the next. `RecipeExtractor.from_url` holds one lock, so this worker and `GET /api/recipes/recipe_url` do not scrape at the same time. Nothing is written to `dish` or `recipe` until keep.

### `POST /api/recipe_imports`

- Purpose: enqueue a page. Returns as soon as the row exists.
- Request body: `{ "url": string }` (`http` or `https`, max 2048 characters)
- Response: `{ "id": int, "url": string, "status": string, "extract": RecipeExtract | null, "error": string | null, "created_at": string }`
- A normalized URL that is already `queued`, `running`, or `ready` returns that row instead of a second job. Normalization drops the fragment and a trailing slash.
- Errors: `400` invalid URL; `403` for a non-admin

### `GET /api/recipe_imports`

- Purpose: rows that are not `kept` or `discarded`, oldest first.
- Response: the same item shape as the POST.
- Errors: `403` for a non-admin

### `POST /api/recipe_imports/{import_id}/keep`

- Purpose: persist a `ready` extract with the same dish match as URL import, then set `status` to `kept` and `recipe_id`.
- Response: the import item.
- Errors: `404` missing row; `400` when the row is not `ready`, or when the dish/recipe checks fail; `403` for a non-admin

### `POST /api/recipe_imports/{import_id}/discard`

- Purpose: set `status` to `discarded` for a `ready` or `failed` row. Does not write a recipe.
- Response: the import item.
- Errors: `404` missing row; `400` when the row is still `queued` or `running`; `403` for a non-admin

### `POST /api/recipes/recipe_image?dish_id=`

- Auth: **admin**
- Purpose: extract a recipe from an uploaded image with the same Gemini model, then persist. `dish_id` is optional and means the same thing as on URL import.
- Request: multipart field `file` (jpeg, png, webp, gif, max 10MB)
- Response: `RecipeFull`
- Errors: `400` empty or unsupported image, `500` on model failure; `401`/`403`

## MCP (not REST)

Streamable HTTP MCP at **`/mcp/`** on the cooking host. Public prod URL: **`https://<domain>/recipes/mcp/`** (homelab strips `/recipes/`). Not under `/api/`.

**Auth (either):**

- **OAuth 2.0** (Grok Bot / Gemini Spark): discovery at `GET /recipes/.well-known/oauth-protected-resource` and `…/oauth-authorization-server`; authorize `GET/POST /recipes/oauth/authorize`; token `POST /recipes/oauth/token` (accepts `client_secret_post`, `client_secret_basic`, or public client + PKCE as sent by OpenAuth); DCR `POST /recipes/oauth/register` (defaults to `token_endpoint_auth_method: none`; redirect URIs must match Gemini or Cursor/Grok Bot callbacks, or `MCP_OAUTH_EXTRA_REDIRECT_URIS`). Protected-resource metadata `resource` is **`https://<domain>/recipes/mcp`** (no trailing slash; must match the connector URL exactly). MCP Bearer access token (`aud=mcp`, admin user).
- **API key:** `MCP_API_KEY` via `Authorization: Bearer …` or `X-MCP-API-Key` (CLI / Cursor `mcp.json` / Grok Bot header fallback).

Unauthenticated MCP → **401** + `WWW-Authenticate` (OAuth metadata URL). No OAuth and no `MCP_API_KEY` → **503**.

### Tool: `create_recipe`

- Purpose: create a recipe under a **dish** (main category) with the same persistence rules as `POST /api/recipes/recipe`.
- Arguments: `recipe_name` (specific recipe), `dish_name` and/or `dish_id` (category), `components[]` (ingredients + instructions).
- Returns: JSON with `id`, `name`, `dish_id`, `components`, `message`.
- Code: `server/app/mcp_server.py`

Full client setup: [features/mcp.md](features/mcp.md).
