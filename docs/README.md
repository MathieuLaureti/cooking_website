# Cooking website docs

Personal cooking console: ingredient pairings (match checker) and a dish/recipe catalog, served through nginx to a React UI and a FastAPI backend on Postgres. **Mobile-first:** the UI and PWA install flow are first-class for phone use in the kitchen—see [Mobile and PWA](features/mobile-pwa.md).

## Agent pipeline

- [Agent system](agents-system.md) — Orchestrator, gates, manifest, delegation
- [Input](input/) — feature ideas and `/discuss` capture
- [Delivery](delivery/) — ship reports per slice
- [Work manifest](work/) — `active-slice.yaml` template

## Features

- [Mobile and PWA](features/mobile-pwa.md) — install on phone, manifest, service worker, `/recipes/` scope
- [Authentication](features/auth.md) — login required, admin registration codes, roles
- [Admin](features/admin.md) — registration code, alias waiting list, and URL import review
- [Recipe URL queue](features/recipe-import.md) — extension button, one-at-a-time extract, keep or discard
- [Match checker](features/match-checker.md) — pairings, plus nutrition facts per 100 g from the Canadian Nutrient File
- [Recipes](features/recipes.md) — dishes, recipes, components, and URL or image import (admin only)
- [MCP](features/mcp.md) — Grok Bot / Gemini Spark / CLI tool to create recipes at `/mcp`

## System

- [Architecture](architecture.md) — containers and request flow
- [Data model](data-model.md) — Postgres tables
- [API](api.md) — every HTTP route as the browser sees it
- [Operations](operations.md) — compose, env, migrations, seed

## Decisions

- [Gemini recipe extract](decisions/2026-09-25-gemini-recipe-extract.md) — Gemma on the Gemini API instead of local Ollama
- [Ingredient identity](decisions/2026-09-25-ingredient-identity.md) — the script saves a `catalog_alias` at confidence 0.75 or higher; lower scores wait on the admin queue. Embeddings are not built
