import asyncio
import base64
import json
import os
import re
from typing import NamedTuple

import httpx
from playwright.async_api import async_playwright

from app.pydantic_models.recipes import RecipeChatRequest, RecipeExtract
from app.gemini_scheduler import GeminiPriority, gemini_scheduler

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
PAGE_CHAR_CAP = 40_000
_MIN_PAGE_TEXT = 350
_JINA_READER_PREFIX = "https://r.jina.ai/"
_READER_FALLBACK_ATTEMPTS = 3
_READER_RETRY_DELAY_SEC = 2.0
_BOT_WALL_PHRASES = (
    "performing security verification",
    "checking your browser",
    "just a moment",
    "enable javascript and cookies",
)
_scrape_lock = asyncio.Lock()


class PageFetchResult(NamedTuple):
    text: str
    structured_ingredients: list[str]


_LD_JSON_SCRIPT = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


def _recipe_nodes_from_ld(data: object) -> list[dict]:
    if isinstance(data, list):
        nodes: list[dict] = []
        for item in data:
            nodes.extend(_recipe_nodes_from_ld(item))
        return nodes
    if not isinstance(data, dict):
        return []
    graph = data.get("@graph")
    if graph is not None:
        return _recipe_nodes_from_ld(graph)
    node_type = data.get("@type")
    types = node_type if isinstance(node_type, list) else [node_type]
    if any(t and "Recipe" in str(t) for t in types):
        return [data]
    main = data.get("mainEntity")
    if main is not None:
        return _recipe_nodes_from_ld(main)
    return []


def _ingredient_strings_from_recipe(recipe: dict) -> list[str]:
    raw = recipe.get("recipeIngredient")
    if raw is None:
        raw = recipe.get("ingredients")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    if not isinstance(raw, list):
        return []
    lines: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            lines.append(item.strip())
        elif isinstance(item, dict):
            name = item.get("name") or item.get("text")
            if name:
                lines.append(str(name).strip())
    return lines


def parse_recipe_jsonld_ingredients(html: str) -> list[str]:
    """Best-effort Schema.org Recipe ingredients from embedded JSON-LD."""
    seen: set[str] = set()
    ordered: list[str] = []
    for match in _LD_JSON_SCRIPT.finditer(html):
        block = match.group(1).strip()
        if not block:
            continue
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        for recipe in _recipe_nodes_from_ld(data):
            for line in _ingredient_strings_from_recipe(recipe):
                key = line.lower()
                if key in seen:
                    continue
                seen.add(key)
                ordered.append(line)
    return ordered


def _structured_ingredients_text(lines: list[str]) -> str:
    body = "\n".join(f"- {line}" for line in lines)
    return (
        "Structured recipe metadata from the page (Schema.org recipeIngredient). "
        "Every line below must appear in components[].ingredients with quantity and unit split when possible:\n"
        f"{body}\n\n"
    )


def _looks_like_bot_wall(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in _BOT_WALL_PHRASES)


def _page_text_usable(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < _MIN_PAGE_TEXT:
        return False
    return not _looks_like_bot_wall(stripped)


def _format_fetch_errors(
    playwright_error: str | None, reader_error: str | None
) -> str:
    parts: list[str] = []
    if playwright_error:
        parts.append(playwright_error)
    if reader_error and reader_error not in parts:
        parts.append(reader_error)
    return "; ".join(parts) if parts else "Web extraction failed"


async def _fetch_reader_fallback(url: str) -> str:
    reader_url = f"{_JINA_READER_PREFIX}{url}"
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        response = await client.get(
            reader_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; CookingWebsiteRecipeImport/1.0)"
                ),
            },
        )
    if response.status_code >= 400:
        raise ValueError(f"Reader fallback HTTP {response.status_code}")
    text = response.text.strip()
    if not _page_text_usable(text):
        raise ValueError("Reader fallback text too short.")
    return text


async def _fetch_reader_fallback_with_retries(url: str) -> str:
    last_error: Exception | None = None
    for attempt in range(_READER_FALLBACK_ATTEMPTS):
        try:
            return await _fetch_reader_fallback(url)
        except Exception as exc:
            last_error = exc
            if attempt + 1 < _READER_FALLBACK_ATTEMPTS:
                await asyncio.sleep(_READER_RETRY_DELAY_SEC)
    if last_error is not None:
        raise last_error
    raise ValueError("Reader fallback failed")

_SYSTEM = (
    "Professional chef. Call emit_recipe once with the recipe from the source. "
    "Include every ingredient from the page Ingredients section and from any structured ingredient list in the user message; "
    "do not stop after the first ingredient or move ingredient lines into instructions only. "
    "Quantities are strings so fractions stay exact ('1/4', '1/2'); whole numbers are digit strings. "
    "No accents in names (café -> cafe). "
    "A recipe may be ingredients with an empty instructions list."
)

_COMPONENT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "name": {"type": "STRING"},
        "ingredients": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "quantity": {"type": "STRING"},
                    "unit": {"type": "STRING"},
                },
                "required": ["name", "quantity", "unit"],
            },
        },
        "instructions": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "step": {"type": "INTEGER"},
                    "text": {"type": "STRING"},
                },
                "required": ["step", "text"],
            },
        },
    },
    "required": ["name", "ingredients", "instructions"],
}


def _function_schema(include_dish_name: bool) -> dict:
    properties = {
        "name": {"type": "STRING", "description": "Recipe title, no accents"},
        "components": {"type": "ARRAY", "items": _COMPONENT_SCHEMA},
    }
    required = ["name", "components"]
    if include_dish_name:
        properties["dish_name"] = {
            "type": "STRING",
            "description": "An existing dish name copied exactly, or a short new dish name with no accents",
        }
        required.append("dish_name")
    return {
        "type": "OBJECT",
        "properties": properties,
        "required": required,
    }


_CHAT_RECIPE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "name": {"type": "STRING", "description": "Recipe title, no accents"},
        "dish_id": {
            "type": "INTEGER",
            "description": "Set to an existing dish id when the recipe belongs to one; omit or null when creating a new dish",
        },
        "dish_name": {
            "type": "STRING",
            "description": "A short new dish name with no accents, used only when dish_id is not set",
        },
        "components": {"type": "ARRAY", "items": _COMPONENT_SCHEMA},
    },
    "required": ["name", "components"],
}

_CHAT_TOOL = {
    "functionDeclarations": [
        {
            "name": "emit_recipes",
            "description": "Return one or more recipe versions for the user's request.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "recipes": {"type": "ARRAY", "items": _CHAT_RECIPE_SCHEMA}
                },
                "required": ["recipes"],
            },
        }
    ]
}


_CHAT_SYSTEM = (
    "You are a professional chef assistant helping build recipes. "
    "Talk to the user naturally to refine the recipe. "
    "When you have a recipe (or several variants) ready, call emit_recipes with one or more versions. "
    "Quantities are strings so fractions stay exact ('1/4', '1/2'); whole numbers are digit strings. "
    "No accents in names (café -> cafe). "
    "A recipe may be ingredients with an empty instructions list."
)


def _catalog_text(dish_names: list[str] | None) -> str:
    if dish_names is None:
        return ""
    lines = "\n".join(f"- {name}" for name in dish_names) or "(none yet)"
    return (
        "Existing dishes:\n"
        f"{lines}\n"
        "If this recipe belongs to one of them, set dish_name to that name copied exactly. "
        "Otherwise set dish_name to a short new dish name.\n\n"
    )


def _args_from_response(body: dict) -> dict:
    if body.get("error"):
        message = body["error"].get("message") or str(body["error"])
        raise ValueError(message)
    feedback = body.get("promptFeedback") or {}
    if feedback.get("blockReason"):
        raise ValueError(f"Model blocked the request: {feedback['blockReason']}")

    candidates = body.get("candidates") or []
    if not candidates:
        raise ValueError("Empty model response")

    parts = (candidates[0].get("content") or {}).get("parts") or []
    for part in parts:
        call = part.get("functionCall") or part.get("function_call")
        if not call:
            continue
        args = call.get("args") or {}
        if isinstance(args, str):
            args = json.loads(args)
        return args

    for part in parts:
        text = part.get("text")
        if not text or part.get("thought"):
            continue
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))

    raise ValueError("Model did not return a recipe")


class RecipeExtractor:
    def __init__(self):
        self.model = os.getenv("GEMINI_MODEL", "gemma-4-31b-it")

    async def fetch_page_for_import(self, url: str) -> PageFetchResult:
        async with _scrape_lock:
            return await self._fetch_text(url)

    async def extract_from_cached_page(
        self,
        fetched: PageFetchResult,
        dish_names: list[str] | None,
        *,
        priority: GeminiPriority = GeminiPriority.INTERACTIVE,
    ) -> RecipeExtract:
        parts: list[dict] = [{"text": f"Page text:\n{fetched.text[:PAGE_CHAR_CAP]}"}]
        if fetched.structured_ingredients:
            parts.insert(
                0,
                {"text": _structured_ingredients_text(fetched.structured_ingredients)},
            )
        return await self._emit(parts, dish_names, priority=priority)

    async def from_url(self, url: str, dish_names: list[str] | None) -> RecipeExtract:
        fetched = await self.fetch_page_for_import(url)
        return await self.extract_from_cached_page(
            fetched, dish_names, priority=GeminiPriority.INTERACTIVE
        )

    async def from_image(
        self, image: bytes, mime: str, dish_names: list[str] | None
    ) -> RecipeExtract:
        encoded = base64.b64encode(image).decode("ascii")
        return await self._emit(
            [
                {"inlineData": {"mimeType": mime, "data": encoded}},
                {"text": "Extract the recipe in this image."},
            ],
            dish_names,
            priority=GeminiPriority.INTERACTIVE,
        )

    async def _emit(
        self,
        parts: list[dict],
        dish_names: list[str] | None,
        *,
        priority: GeminiPriority = GeminiPriority.INTERACTIVE,
    ) -> RecipeExtract:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY is not set")

        user_parts = []
        catalog = _catalog_text(dish_names)
        if catalog:
            user_parts.append({"text": catalog})
        user_parts.extend(parts)

        payload = {
            "systemInstruction": {"parts": [{"text": _SYSTEM}]},
            "contents": [{"role": "user", "parts": user_parts}],
            "tools": [
                {
                    "functionDeclarations": [
                        {
                            "name": "emit_recipe",
                            "description": "Return the extracted recipe.",
                            "parameters": _function_schema(dish_names is not None),
                        }
                    ]
                }
            ],
            "toolConfig": {
                "functionCallingConfig": {
                    "mode": "ANY",
                    "allowedFunctionNames": ["emit_recipe"],
                }
            },
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 8192,
                "thinkingConfig": {"thinkingLevel": "minimal"},
            },
        }

        endpoint = GEMINI_URL.format(model=self.model)

        async def call() -> RecipeExtract:
            body = await _gemini_post(endpoint, key, payload)
            args = _stringify_quantities(_args_from_response(body))
            if dish_names is None:
                args.pop("dish_name", None)
            return RecipeExtract.model_validate(args)

        return await gemini_scheduler.run(priority, call)

    async def chat(
        self, request: RecipeChatRequest, dish_context: str
    ) -> tuple[str, list[RecipeExtract]]:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY is not set")

        contents = []
        for turn in request.history:
            role = "model" if turn.role == "model" else "user"
            contents.append({"role": role, "parts": [{"text": turn.text}]})

        user_parts = []
        if dish_context:
            user_parts.append({"text": dish_context})
        if request.current_recipe is not None:
            user_parts.append(
                {
                    "text": (
                        "Current recipe draft (the user can edit this; modify it "
                        "when they ask for changes):\n"
                        + json.dumps(request.current_recipe.model_dump())
                    )
                }
            )
        user_parts.append({"text": request.message})
        contents.append({"role": "user", "parts": user_parts})

        payload = {
            "systemInstruction": {"parts": [{"text": _CHAT_SYSTEM}]},
            "contents": contents,
            "tools": [_CHAT_TOOL],
            "toolConfig": {
                "functionCallingConfig": {
                    "mode": "AUTO",
                }
            },
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 8192,
                "thinkingConfig": {"thinkingLevel": "minimal"},
            },
        }

        endpoint = GEMINI_URL.format(model=self.model)

        async def call() -> tuple[str, list[RecipeExtract]]:
            body = await _gemini_post(endpoint, key, payload)
            return _parse_chat_response(body)

        reply, recipes = await gemini_scheduler.run(GeminiPriority.INTERACTIVE, call)
        validated: list[RecipeExtract] = []
        for recipe in recipes:
            _stringify_quantities(recipe)
            _normalize_extract_dict(recipe)
            try:
                validated.append(RecipeExtract.model_validate(recipe))
            except Exception:
                continue
        return reply, validated

    async def _fetch_text(self, url: str) -> PageFetchResult:
        playwright_error: str | None = None
        structured: list[str] = []
        try:
            extracted_text, structured = await self._fetch_text_playwright(url)
            if _page_text_usable(extracted_text):
                return PageFetchResult(extracted_text, structured)
            playwright_error = "Extracted text too short."
        except Exception as e:
            playwright_error = str(e)

        try:
            text = await _fetch_reader_fallback_with_retries(url)
            return PageFetchResult(text, [])
        except Exception as reader_error:
            detail = _format_fetch_errors(playwright_error, str(reader_error))
            raise ValueError(f"Web extraction failed: {detail}") from reader_error

    async def _fetch_text_playwright(self, url: str) -> tuple[str, list[str]]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                args=[
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--single-process",
                ]
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                try:
                    await page.wait_for_function(
                        """() => {
                        const t = document.body?.innerText || '';
                        if (t.length < 350) return false;
                        const lower = t.toLowerCase();
                        if (lower.includes('performing security verification')) return false;
                        if (lower.includes('checking your browser') && t.length < 2500) {
                            return false;
                        }
                        return true;
                    }""",
                        timeout=45000,
                    )
                except Exception:
                    pass
                html = await page.content()
                structured = parse_recipe_jsonld_ingredients(html)
                await page.evaluate(
                    """() => {
                    const tags = ["script", "style", "header", "footer", "nav", "aside"];
                    tags.forEach(t => document.querySelectorAll(t).forEach(el => el.remove()));
                }"""
                )
                body_text = await page.inner_text("body")
                return body_text, structured
            finally:
                await browser.close()


async def _gemini_post(endpoint: str, api_key: str, payload: dict) -> dict:
    last_error = "Gemini request failed"
    async with httpx.AsyncClient(timeout=120.0) as client:
        for attempt in range(4):
            response = await client.post(
                endpoint,
                headers={"x-goog-api-key": api_key},
                json=payload,
            )
            if response.status_code == 200:
                return response.json()

            last_error = response.text[:800]
            retryable = response.status_code in (429, 500, 503)
            if not retryable or attempt == 3:
                break
            try:
                err = response.json().get("error", {})
                msg = (err.get("message") or "").lower()
                if response.status_code == 500 and "internal" not in msg:
                    break
            except Exception:
                pass
            await asyncio.sleep(1.5 * (attempt + 1))

    raise ValueError(last_error)


def _normalize_extract_dict(recipe: dict) -> None:
    if not recipe.get("name"):
        for key in ("title", "recipe_name", "recipe_title"):
            if recipe.get(key):
                recipe["name"] = str(recipe.pop(key))
                break
    if not recipe.get("name"):
        recipe["name"] = "Untitled recipe"
    if recipe.get("dish_id") in (0, "0", ""):
        recipe["dish_id"] = None
    if recipe.get("dish_name") is None:
        recipe["dish_name"] = ""


def _stringify_quantities(args: dict) -> dict:
    for component in args.get("components") or []:
        component.setdefault("ingredients", [])
        component.setdefault("instructions", [])
        for ingredient in component["ingredients"]:
            if ingredient.get("quantity") is not None:
                ingredient["quantity"] = str(ingredient["quantity"])
    return args


def _parse_chat_response(body: dict) -> tuple[str, list[dict]]:
    if body.get("error"):
        message = body["error"].get("message") or str(body["error"])
        raise ValueError(message)
    feedback = body.get("promptFeedback") or {}
    if feedback.get("blockReason"):
        raise ValueError(f"Model blocked the request: {feedback['blockReason']}")

    candidates = body.get("candidates") or []
    if not candidates:
        raise ValueError("Empty model response")

    parts = (candidates[0].get("content") or {}).get("parts") or []
    reply_parts = []
    recipes: list[dict] = []
    for part in parts:
        call = part.get("functionCall") or part.get("function_call")
        if call and (call.get("name") or call.get("function_name")) == "emit_recipes":
            args = call.get("args") or {}
            if isinstance(args, str):
                args = json.loads(args)
            for recipe in args.get("recipes") or []:
                if isinstance(recipe, str):
                    recipe = json.loads(recipe)
                recipes.append(recipe)
            continue
        text = part.get("text")
        if text and not part.get("thought"):
            reply_parts.append(text)

    return "\n".join(reply_parts).strip(), recipes
