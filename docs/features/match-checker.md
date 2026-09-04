# Match checker

## What it does

Lets you search a seeded catalog of ingredients and see pairing **affinities**, things to **avoid**, and **match scores** (1–4) against other ingredients. Requires login (any role).

## User flow

1. Sign in (see [auth](auth.md)).
2. Page load fetches the short ingredient list.
3. Typing filters titles client-side (`includes`, case-insensitive) and focuses this panel (`isActive`).
4. Clicking a row loads the full record and shows affinities, avoid, and scored matches.
5. Clear returns to search.

Only one of match-checker / recipes is “active” at a time (`console/src/App.tsx`).

## UI

- `console/src/components/match_checker.tsx` — search, list, detail.
- API calls via `console/src/api/client.ts` with Bearer token (`API_BASE = '/api/match_checker'`).
- Score colors: 4 orange, 3 gold, 2 light, else muted.

## Backend

- Router: `server/app/router/match_checker.py` — two GET routes, no writes.
- Auth: `Depends(get_current_user)` on both routes.
- Model: `MatchChecker` in `server/app/db_models/models.py`.
- No Redis, no Ollama.

## Data

Table `match_checker`. Seeded from legacy SQLite `api_ingredient` via `python -m app.sqlitetopostgres`. See [data model](../data-model.md).

## Edge cases

- Empty `avoid` / `affinities` / `matches` are valid (many seed rows).
- Unknown `id` → 404; the UI does not surface that as a message.
- No create/update/delete API; changing pairings means a DB write or re-seed.
- Unauthenticated request → 401.
