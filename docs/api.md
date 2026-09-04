# API

JWT Bearer authentication on all routes except `/health`, `POST /auth/login`, and `POST /auth/register`.

Send `Authorization: Bearer <token>` on every authenticated request. Token payload includes `sub` (user id), `username`, `role`, `exp`. Protected routes decode the JWT only — no per-request database lookup.

Pydantic shapes: `server/app/pydantic_models/auth.py`, `server/app/pydantic_models/match_checker.py`, `server/app/pydantic_models/recipes.py`.

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

## Recipes — dishes

Code: `server/app/router/recipes.py`. Prefix `/recipes`.

### `GET /api/recipes/dishes`

- Auth: Bearer (any role)
- Purpose: list dishes.
- Response: `[{ "id": int, "name": string }, ...]`
- Cache: Redis key `dishes:all`, TTL 3600s.

### `POST /api/recipes/dish`

- Auth: **admin**
- Purpose: create a dish.
- Request body: `{ "name": string }`
- Response: `{ "id": int, "name": string }`
- Errors: `400` duplicate name; `401`/`403`

### `PUT /api/recipes/dish_edit/{dish_id}`

- Auth: **admin**
- Purpose: rename a dish.
- Errors: `404` `"Dish not found"`; `401`/`403`

### `DELETE /api/recipes/dish/{dish_id}`

- Auth: **admin**
- Purpose: delete a dish with no recipes.
- Errors: `404`, `400` if recipes exist; `401`/`403`

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
- Response: `[{ "id": int, "name": string }, ...]`
- Cache: `dish_recipes:{dish_id}`, TTL 3600s.

### `GET /api/recipes/recipe/{recipe_id}`

- Auth: Bearer (any role)
- Response: `RecipeFull`
- Cache: `full_recipe:{recipe_id}`, TTL 3600s.
- Errors: `404` `"Recipe not found"`

### `POST /api/recipes/recipe/{dish_id}`

- Auth: **admin**
- Purpose: manual create.
- Errors: `404`, `400` duplicate name; `401`/`403`

### `PUT /api/recipes/recipe_edit/{recipe_id}`

- Auth: **admin**
- Purpose: replace name and rebuild all components.
- Errors: `404`; `401`/`403`

### `DELETE /api/recipes/recipe/{recipe_id}`

- Auth: **admin**
- Errors: `404`; `401`/`403`

### `GET /api/recipes/recipe_url/{dish_id}?url=`

- Auth: **admin**
- Purpose: scrape URL via Playwright + Ollama, then persist.
- Errors: `500` on scrape/LLM failure; `401`/`403`

There is **no** `POST /api/recipes/recipe_image/{dish_id}` on the server yet.
