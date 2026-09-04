# Cooking website docs

Personal cooking console: ingredient pairings (match checker) and a dish/recipe catalog, served through nginx to a React UI and a FastAPI backend on Postgres.

## Features

- [Match checker](features/match-checker.md) — look up ingredient affinities, avoids, and pairing scores
- [Recipes](features/recipes.md) — dishes, recipes, components, and URL import

## System

- [Architecture](architecture.md) — containers and request flow
- [Data model](data-model.md) — Postgres tables
- [API](api.md) — every HTTP route as the browser sees it
- [Operations](operations.md) — compose, env, migrations, seed
