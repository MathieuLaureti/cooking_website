from app.catalog_sanity import (
    SanityDrop,
    apply_layer1,
    classify_foods,
    cluster_key,
    layer3_criteria,
    rule_egg_group,
)
from app.ingredient_match import focus_criteria
from app.ingredient_match import Food


def _food(name_en: str, *, group_code: str = "1", group_en: str = "Dairy and Egg Products") -> Food:
    parts = tuple(part.strip() for part in name_en.split(",") if part.strip())
    return Food(
        id=1,
        name_en=name_en,
        name_fr=name_en,
        group_code=group_code,
        group_en=group_en,
        group_fr=group_en,
        parts=parts,
    )


def test_layer1_drops_dried_chicken_egg():
    food = _food("Egg, chicken, dried, whole")
    assert apply_layer1(food) == "egg_dehydrated_or_powder"


def test_layer1_drops_raw_chicken_egg():
    food = _food("Egg, chicken, whole, fresh or frozen, raw")
    assert rule_egg_group(food) == "egg_fresh_raw"


def test_layer1_keeps_cooked_chicken_egg():
    food = _food("Egg, chicken, whole, cooked, boiled in shell, hard-cooked")
    assert apply_layer1(food) is None


def test_layer1_keeps_dried_fruit_in_fruit_group():
    food = _food("Apricots, dried, sulfured, stewed, with added sugar", group_code="9", group_en="Fruits")
    assert apply_layer1(food) is None


def test_layer3_criteria_survives_focus_criteria():
    food = _food("Egg, chicken, whole, cooked, poached")
    narrowed = focus_criteria(food.name_en, layer3_criteria())
    assert "none" in narrowed


def test_cluster_key_uses_first_two_segments():
    food = _food("Egg, chicken, whole, fresh or frozen, raw")
    assert cluster_key(food, depth=2) == "egg chicken"


async def test_classify_dedupes_layers():
    foods = [
        Food(
            id=10,
            name_en="Egg, chicken, dried, whole",
            name_fr="x",
            group_code="1",
            group_en="Dairy",
            group_fr="Dairy",
            parts=("Egg", "chicken", "dried", "whole"),
        ),
        Food(
            id=11,
            name_en="Egg, chicken, whole, fresh or frozen, raw",
            name_fr="x",
            group_code="1",
            group_en="Dairy",
            group_fr="Dairy",
            parts=("Egg", "chicken", "whole", "fresh or frozen", "raw"),
        ),
        Food(
            id=12,
            name_en="Egg, chicken, whole, cooked, poached",
            name_fr="x",
            group_code="1",
            group_en="Dairy",
            group_fr="Dairy",
            parts=("Egg", "chicken", "whole", "cooked", "poached"),
        ),
    ]
    drops = await classify_foods(foods, use_laya=False)
    dropped_ids = {row.food.id for row in drops}
    assert dropped_ids == {10, 11}
    assert all(isinstance(row, SanityDrop) for row in drops)
