---
name: recipe-via-mcp
description: >-
  Draft recipes (dish_name, recipe_name, components) and persist via MCP
  create_recipe. Use when the user wants a new recipe saved to the cooking
  catalog, or asks to push/submit a recipe through MCP.
---

# Recipe creation → MCP

## Terminology

| Term | MCP field |
|------|-----------|
| Dish (category) | `dish_name` |
| Recipe (one preparation) | `recipe_name` |

## Workflow

1. Clarify dish and recipe names if needed.
2. Structure **components** (ingredients + numbered steps).
3. Show a short draft if the user has not approved yet.
4. **Persist:** call MCP **`create_recipe`** (or **`ping`** first if connectivity is uncertain).

## MCP endpoint (prod)

`https://www.homelabdu204.ca/recipes/mcp/`

- **Grok Bot:** OAuth custom plugin at this URL (Marketplace / Settings → Plugins). Attach with `@` in chat. Admin Cooking login. Not grok.com connectors unless that surface is configured separately.
- **Gemini Spark:** OAuth connected app only — not regular Gemini chat.
- **Cursor IDE / CLI:** `MCP_API_KEY` in `.env`, Bearer header, if OAuth is not used.

## Payload shape

```json
{
  "recipe_name": "Title",
  "dish_name": "Category",
  "components": [
    {
      "name": "Main",
      "ingredients": [{ "name": "olive oil", "quantity": "2", "unit": "tbsp" }],
      "instructions": [{ "step": 1, "text": "Heat oil." }]
    }
  ]
}
```

If **`create_recipe`** is not available in this session, say so and output the JSON above for the user to run in **Grok Bot** (plugin attached) or **Gemini Spark** with the homelab app attached.
