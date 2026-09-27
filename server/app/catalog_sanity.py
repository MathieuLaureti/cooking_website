"""Layered pass to flag CNF foods that are not home-recipe catalog rows.

Preview only — nothing is written to the database. See ``scripts/catalog_sanity_preview.py``.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.ingredient_match import AUTO_ACCEPT, NONE, Food, decide
from app.seed_cnf import normalize_name

ProgressCallback = Callable[[str, int, int, int], Awaitable[None] | None]

# CNF groups where dried / dehydrated forms are normal pantry items.
DRIED_OK_GROUP_CODES = frozenset({"2", "9", "11", "12", "16", "20"})

INDUSTRIAL_PHRASES = (
    "glucose reduced",
    "pan dried",
    "liquid egg product",
)

INDUSTRIAL_WORDS = frozenset(
    {
        "dehydrated",
        "deshydrate",
        "deshydrated",
        "desiccated",
        "dried",
        "flakes",
        "powder",
        "stabilised",
        "stabilized",
    }
)

EGG_INDUSTRIAL_FRAGMENTS = (
    "scrambled, frozen",
    "western omelet",
    "spanish omelet",
    "omelet, with",
)


@dataclass(frozen=True)
class SanityDrop:
    food: Food
    layer: str
    reason: str


def drop_to_dict(drop: SanityDrop) -> dict:
    food = drop.food
    return {
        "food_id": food.id,
        "layer": drop.layer,
        "reason": drop.reason,
        "name_en": food.name_en,
        "name_fr": food.name_fr,
        "group_en": food.group_en,
    }


async def _emit_progress(
    on_progress: ProgressCallback | None,
    layer: str,
    current: int,
    total: int,
    drops_count: int,
) -> None:
    if on_progress is None:
        return
    result = on_progress(layer, current, total, drops_count)
    if asyncio.iscoroutine(result):
        await result


def comma_parts(name_en: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in name_en.split(",") if part.strip())


def cluster_key(food: Food, depth: int = 2) -> str:
    parts = food.parts or comma_parts(food.name_en)
    head = parts[:depth]
    if not head:
        return normalize_name(food.name_en)
    return normalize_name(", ".join(head))


def _normalized_blob(food: Food) -> str:
    return normalize_name(food.name_en)


def _is_egg_row(food: Food) -> bool:
    parts = food.parts or comma_parts(food.name_en)
    return bool(parts) and normalize_name(parts[0]) == "egg"


def segment_industrial_dried(segment: str) -> bool:
    norm = normalize_name(segment)
    if not norm:
        return False
    for phrase in INDUSTRIAL_PHRASES:
        if phrase in norm:
            return True
    tokens = set(norm.split())
    return bool(tokens & INDUSTRIAL_WORDS)


def rule_industrial_dried_form(food: Food) -> str | None:
    if food.group_code in DRIED_OK_GROUP_CODES:
        return None
    for part in food.parts or comma_parts(food.name_en):
        if segment_industrial_dried(part):
            return "industrial_dried_or_powder_form"
    return None


def rule_egg_group(food: Food) -> str | None:
    if food.group_code != "1" or not _is_egg_row(food):
        return None
    blob = _normalized_blob(food)
    for fragment in EGG_INDUSTRIAL_FRAGMENTS:
        if normalize_name(fragment) in blob:
            return "egg_industrial_or_ready_meal"
    if "liquid egg product" in blob:
        return "egg_industrial_liquid_product"
    if " raw" in f" {blob} " or blob.endswith(" raw"):
        if "cooked" not in blob:
            return "egg_fresh_raw"
    for part in food.parts or comma_parts(food.name_en):
        if segment_industrial_dried(part):
            return "egg_dehydrated_or_powder"
    return None


def rule_baby_food(food: Food) -> str | None:
    if food.group_code == "3":
        return "babyfood_group"
    return None


def apply_layer1(food: Food) -> str | None:
    for rule in (rule_baby_food, rule_egg_group, rule_industrial_dried_form):
        hit = rule(food)
        if hit is not None:
            return hit
    return None


def apply_layer2_cluster(
    survivors: list[Food],
) -> list[SanityDrop]:
    """Drop obvious formulation rows that share a narrow cluster prefix."""
    by_key: dict[str, list[Food]] = defaultdict(list)
    for food in survivors:
        by_key[cluster_key(food, depth=3)].append(food)

    drops: list[SanityDrop] = []
    for _key, rows in by_key.items():
        if len(rows) < 2:
            continue
        if not all(_is_egg_row(row) for row in rows):
            continue
        for food in rows:
            blob = _normalized_blob(food)
            if "fat free" in blob or "frozen mixture" in blob:
                drops.append(SanityDrop(food, "layer2", "egg_cluster_industrial_variant"))
    return drops


def layer3_criteria() -> dict[str, str]:
    yes, no = "yes", "no"
    return {
        yes: "Yes — normal home pantry or grocery item in this form",
        no: "No — industrial, dehydrated matrix, or not used as a home recipe ingredient",
        NONE: "Unclear — cannot classify",
    }


def apply_layer3_laya(food: Food) -> SanityDrop | None:
    yes, no = "yes", "no"
    choice, confidence, _probabilities = decide(
        food.name_en,
        (
            "For everyday home cooking (recipe shopping list), is this exact CNF product "
            "something people actually buy or stock — not a factory formulation?"
        ),
        layer3_criteria(),
    )
    if choice != no or confidence is None or confidence < AUTO_ACCEPT:
        return None
    return SanityDrop(food, "layer3", "laya_not_home_cooking")


async def classify_foods(
    foods: list[Food],
    *,
    use_laya: bool = False,
    on_progress: ProgressCallback | None = None,
) -> list[SanityDrop]:
    """Return all foods the pipeline would hide from a cooking catalog."""
    drops: list[SanityDrop] = []
    seen_ids: set[int] = set()
    survivors: list[Food] = []
    total_foods = len(foods)

    for index, food in enumerate(foods, start=1):
        reason = apply_layer1(food)
        if reason is not None:
            drops.append(SanityDrop(food, "layer1", reason))
            seen_ids.add(food.id)
        else:
            survivors.append(food)
        if index == total_foods or index % 250 == 0:
            await _emit_progress(on_progress, "Layer 1", index, total_foods, len(drops))

    await _emit_progress(on_progress, "Layer 2", 0, 1, len(drops))
    for drop in apply_layer2_cluster(survivors):
        if drop.food.id in seen_ids:
            continue
        drops.append(drop)
        seen_ids.add(drop.food.id)
    await _emit_progress(on_progress, "Layer 2", 1, 1, len(drops))

    if use_laya:
        laya_queue = [food for food in survivors if food.id not in seen_ids]
        layer_total = len(laya_queue)
        for index, food in enumerate(laya_queue, start=1):
            hit = await asyncio.to_thread(apply_layer3_laya, food)
            if hit is not None:
                drops.append(hit)
                seen_ids.add(food.id)
            await _emit_progress(on_progress, "Layer 3", index, layer_total, len(drops))

    drops.sort(key=lambda row: (row.food.name_en.lower(), row.food.id))
    return drops
