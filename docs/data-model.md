# Data model

Postgres. Source of truth: `server/app/db_models/models.py` and `server/alembic/versions/`.

Two domains share one database: **recipes** (dish → recipe → component → ingredients/instructions) and **match checker** (standalone pairing table). They do not share foreign keys.

```
dish 1──* recipe 1──* recipe_component 1──* ingredient
                                   └────────* instruction

match_checker   (independent)

user            (independent — auth)
```

## Tables

### `dish`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | integer | PK |
| `name` | `varchar(255)` | unique, nullable in schema |

- Relationships: `recipes` → `recipe` (`cascade="all, delete-orphan"` at ORM level).
- Notes: unique name added in `7f2e4e528ece`. The delete-dish API still refuses if any recipe exists; ORM cascade is not a DB `ON DELETE CASCADE` (the cascade Alembic revision is a no-op).

### `recipe`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | integer | PK |
| `dish_id` | integer | FK `dish.id`, not null |
| `name` | `varchar(255)` | nullable |

- Relationships: `dish`; `components` → `recipe_component` (ORM cascade delete-orphan).
- Notes: create-recipe rejects a duplicate `(dish_id, name)` in application code; there is no unique constraint on that pair.

### `recipe_component`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | integer | PK |
| `recipe_id` | integer | FK `recipe.id`, not null |
| `name` | `varchar(255)` | nullable |

- Relationships: `recipe`; `ingredients`; `instructions` (both ORM cascade delete-orphan).
- Notes: `name` added in `ba08389779eb`. A recipe is a list of components (e.g. sauce vs dough).

### `ingredient`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | integer | PK |
| `component_id` | integer | FK `recipe_component.id`, not null |
| `name` | `varchar(255)` | not null |
| `quantity` | `varchar(50)` | not null |
| `unit` | `varchar(50)` | not null |

- Relationships: `component`.
- Notes: `quantity` is a string so values like `"1/2"` work (`7bce26ea193d`). This table is **recipe line items**, not match-checker ingredients.

### `instruction`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | integer | PK |
| `component_id` | integer | FK `recipe_component.id`, not null |
| `step` | integer | not null |
| `text` | text | not null |

- Relationships: `component`.

### `match_checker`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | integer | PK |
| `title` | text | indexed, not null |
| `avoid` | `text[]` | not null, server default `{}` |
| `affinities` | `text[]` | not null, server default `{}` |
| `matches` | jsonb | not null, server default `[]` |

- Relationships: none.
- Notes: created in `946b70e36b6f`. `matches` is a list of `[name, score]` pairs (score typically 1–4). Title is indexed, not unique.

### `user`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | integer | PK |
| `username` | `varchar(64)` | unique, not null |
| `password_hash` | `varchar(255)` | not null (bcrypt) |
| `role` | `varchar(16)` | not null — `admin` or `user` |

- Relationships: none.
- Notes: added in `c3a8f1d92e04`. Passwords stored as bcrypt hashes. First admin bootstrapped from `ADMIN_USERNAME` / `ADMIN_PASSWORD` env vars when the table is empty.

## Legacy / seed

- File: `server/db.sqlite3`, Django table `api_ingredient` (`title`, `avoid`, `afinities`, `matchs` — original spellings).
- Import: `docker compose exec server python -m app.sqlitetopostgres` (`server/app/sqlitetopostgres.py`).
- Maps JSON text columns onto `avoid` / `affinities` / `matches`. Skips if `match_checker` already has rows.
