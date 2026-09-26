"""Seed Canadian Nutrient File 2026 into the catalog tables.

Run from the server container:

    docker compose exec server python -m app.seed_cnf

Skips when any catalog_food row with source ``cnf`` already exists.
Nutrient amounts are stored per 100 g, as published.
"""
from __future__ import annotations

import asyncio
import csv
import re
import sys
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import func, insert, select

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import AsyncSessionLocal
from app.db_models.models import (
    CatalogAlias,
    CatalogFood,
    CatalogFoodNutrient,
    CatalogNutrient,
)

SEED_DIR = ROOT / "seed" / "cnf"
SOURCE = "cnf"
AMOUNT_BATCH = 5000

_PUNCT = re.compile(r"[^a-z0-9]+")


def normalize_name(name: str) -> str:
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _PUNCT.sub(" ", text.lower())
    return " ".join(text.split())


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = [column.strip() for column in next(reader)]
        for row in reader:
            yield dict(zip(header, row))


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _require(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"CNF seed file not found at {path}")


def load_groups() -> dict[str, tuple[str, str]]:
    path = SEED_DIR / "cnf_food_group.csv"
    _require(path)
    groups: dict[str, tuple[str, str]] = {}
    for row in read_csv(path):
        code = row["CNF_Food_Group_Code"].strip()
        groups[code] = (
            row["CNF_Food_Group_Description_EN"].strip(),
            row["CNF_Food_Group_Description_FR"].strip(),
        )
    return groups


def food_rows(groups: dict[str, tuple[str, str]]) -> list[dict]:
    path = SEED_DIR / "food_name.csv"
    _require(path)
    rows = []
    for row in read_csv(path):
        code = row["Food_Code"].strip()
        group_code = _optional(row.get("CNF_Food_Group_Code"))
        group_en, group_fr = groups.get(group_code or "", (None, None))
        rows.append(
            {
                "source": SOURCE,
                "external_code": code,
                "name_en": row["Food_Description_EN"].strip(),
                "name_fr": row["Food_Description_FR"].strip(),
                "group_code": group_code,
                "group_en": group_en,
                "group_fr": group_fr,
            }
        )
    return rows


def nutrient_rows() -> list[dict]:
    path = SEED_DIR / "nutrient_name.csv"
    _require(path)
    rows = []
    for row in read_csv(path):
        decimals = _optional(row.get("Nutrient_Decimals"))
        rows.append(
            {
                "source": SOURCE,
                "external_code": row["Nutrient_Code"].strip(),
                "symbol": _optional(row.get("Nutrient_Symbol")),
                "name_en": row["Nutrient_Name_EN"].strip(),
                "name_fr": row["Nutrient_Name_FR"].strip(),
                "unit": row["Nutrient_Unit"].strip(),
                "decimals": int(decimals) if decimals is not None else None,
                "tagname": _optional(row.get("Tagname")),
            }
        )
    return rows


def alias_rows(food_ids: dict[str, int], foods: list[dict]) -> tuple[list[dict], int]:
    seen: set[str] = set()
    rows: list[dict] = []
    skipped = 0
    for food in foods:
        food_id = food_ids[food["external_code"]]
        for locale, published in (("en", food["name_en"]), ("fr", food["name_fr"])):
            if not published:
                continue
            normalized = normalize_name(published)
            if not normalized or normalized in seen:
                skipped += 1
                continue
            seen.add(normalized)
            rows.append(
                {
                    "food_id": food_id,
                    "name": published,
                    "normalized": normalized,
                    "locale": locale,
                }
            )
    return rows, skipped


async def _insert_batches(db, model, rows: list[dict], size: int) -> None:
    for start in range(0, len(rows), size):
        await db.execute(insert(model), rows[start : start + size])


async def _id_map(db, model, codes: list[str]) -> dict[str, int]:
    result = await db.execute(
        select(model.external_code, model.id).where(
            model.source == SOURCE, model.external_code.in_(codes)
        )
    )
    return {code: row_id for code, row_id in result.all()}


async def insert_amounts(db, food_ids: dict[str, int], nutrient_ids: dict[str, int]) -> tuple[int, int]:
    path = SEED_DIR / "nutrient_amount.csv"
    _require(path)
    written = 0
    skipped = 0
    batch: list[dict] = []

    async def flush() -> None:
        nonlocal written
        if not batch:
            return
        await db.execute(insert(CatalogFoodNutrient), batch)
        written += len(batch)
        batch.clear()

    for row in read_csv(path):
        food_id = food_ids.get(row["Food_Code"].strip())
        nutrient_id = nutrient_ids.get(row["Nutrient_Code"].strip())
        raw = row["Nutrient_Amount"].strip()
        if food_id is None or nutrient_id is None or not raw:
            skipped += 1
            continue
        try:
            amount = Decimal(raw)
        except InvalidOperation:
            skipped += 1
            continue
        batch.append(
            {
                "food_id": food_id,
                "nutrient_id": nutrient_id,
                "amount_per_100g": amount,
            }
        )
        if len(batch) >= AMOUNT_BATCH:
            await flush()
    await flush()
    return written, skipped


async def seed() -> None:
    groups = load_groups()
    foods = food_rows(groups)
    nutrients = nutrient_rows()

    async with AsyncSessionLocal() as db:
        existing = await db.scalar(
            select(func.count())
            .select_from(CatalogFood)
            .where(CatalogFood.source == SOURCE)
        )
        if existing:
            print(f"catalog_food already has {existing} cnf rows; skipping import.")
            return

        await _insert_batches(db, CatalogFood, foods, 500)
        await _insert_batches(db, CatalogNutrient, nutrients, 500)
        food_ids = await _id_map(db, CatalogFood, [row["external_code"] for row in foods])
        nutrient_ids = await _id_map(
            db, CatalogNutrient, [row["external_code"] for row in nutrients]
        )
        amount_count, amount_skipped = await insert_amounts(db, food_ids, nutrient_ids)
        aliases, alias_skipped = alias_rows(food_ids, foods)
        if aliases:
            await _insert_batches(db, CatalogAlias, aliases, 1000)
        await db.commit()
        print(
            f"Seeded CNF: {len(foods)} foods, {len(nutrients)} nutrients, "
            f"{amount_count} amounts, {len(aliases)} aliases "
            f"(skipped amounts={amount_skipped}, alias collisions={alias_skipped})."
        )


if __name__ == "__main__":
    asyncio.run(seed())
