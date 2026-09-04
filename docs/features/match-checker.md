# Match checker

## What it does

Lets you search a seeded catalog of ingredients and see pairing **affinities**, things to **avoid**, and **match scores** (1–4) against other ingredients.

## User flow

1. Page load fetches the short ingredient list.
2. Typing filters titles client-side (`includes`, case-insensitive) and focuses this panel (`isActive`).
3. Clicking a row loads the full record and shows affinities, avoid, and scored matches.
4. Clear returns to search.

Only one of match-checker / recipes is “active” at a time (`console/src/App.tsx`).

## UI

- `console/src/components/match_checker.tsx` — search, list, detail.
- Client types live in that file: `{ id, title }` and `{ id, title, avoid[], affinities[], matches: [string, number][] }`.
- Score colors: 4 orange, 3 gold, 2 light, else muted.
- `API_BASE = '/api/match_checker'`.

## Backend

- Router: `server/app/router/match_checker.py` — two GET routes, no writes.
- Model: `MatchChecker` in `server/app/db_models/models.py`.
- No Redis, no Ollama.

## Data

Table `match_checker`. Seeded from legacy SQLite `api_ingredient` via `python -m app.sqlitetopostgres`. See [data model](../data-model.md).

## Edge cases

- Empty `avoid` / `affinities` / `matches` are valid (many seed rows).
- Unknown `id` → 404; the UI does not surface that as a message.
- No create/update/delete API; changing pairings means a DB write or re-seed (re-seed is skipped if rows already exist).
