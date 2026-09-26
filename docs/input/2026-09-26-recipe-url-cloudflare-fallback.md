# Recipe URL import: Cloudflare-protected sites

## Status
ready-for-github

## Summary

Recipe URL import (extension queue and draft-form `GET /api/recipes/recipe_url`) uses Playwright to read page text. Sites behind Cloudflare bot checks (for example Sally's Baking Addiction) return only the challenge page, so extraction fails with **Extracted text too short.**

## Detailed intent

When Playwright body text is below the minimum length or matches known bot-wall phrases, retry fetch through the Jina reader proxy (`r.jina.ai`) before sending text to Gemini. Keep Playwright as the primary path for sites that do not block headless Chromium.

## Acceptance criteria

### Scenario: Cloudflare-blocked recipe URL

- **Given** a recipe URL that serves a Cloudflare challenge to headless Playwright
- **When** `RecipeExtractor.from_url` runs
- **Then** the server obtains usable recipe page text via the reader fallback and Gemini can extract ingredients and steps

### Scenario: Normal site unchanged

- **Given** a recipe URL that Playwright can read with sufficient body text
- **When** `RecipeExtractor.from_url` runs
- **Then** the reader fallback is not required and behavior matches the previous Playwright-only path

## Out of scope

- General anti-bot evasion beyond this reader fallback
- Changing Gemini models or import queue UX

## Notes

- Repro URL: `https://sallysbakingaddiction.com/homemade-salted-caramel-recipe/`
- Feature batch: `recipe-url-cloudflare-fallback`
