"""Print CNF foods the cooking-catalog sanity pipeline would hide.

Layer 1–2 are deterministic rules. Layer 3 calls Laya (same service as ingredient match)
when ``--laya`` is passed. Nothing is written to the database.

    docker compose exec server python scripts/catalog_sanity_preview.py
    docker compose exec server python scripts/catalog_sanity_preview.py --laya
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.catalog_sanity import classify_foods
from app.database import engine
from app.ingredient_match import load_foods


def _print_rows(rows) -> None:
    for drop in rows:
        food = drop.food
        print(
            f"{food.id}\t{drop.layer}\t{drop.reason}\t{food.name_en}\t{food.name_fr}\t{food.group_en}"
        )


async def _main(use_laya: bool) -> int:
    foods = await load_foods()
    if not foods:
        print("No CNF foods in catalog (run seed_cnf first).", file=sys.stderr)
        return 1
    drops = await classify_foods(foods, use_laya=use_laya)
    print("id\tlayer\treason\tname_en\tname_fr\tgroup_en")
    _print_rows(drops)
    print(
        f"\n# total_cnf={len(foods)} dropped={len(drops)} laya={'on' if use_laya else 'off'}",
        file=sys.stderr,
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview CNF rows hidden by catalog sanity rules.")
    parser.add_argument(
        "--laya",
        action="store_true",
        help="Run layer 3 (Laya) on survivors after rules — slow; needs decide API.",
    )
    args = parser.parse_args()

    async def run() -> int:
        try:
            return await _main(args.laya)
        finally:
            await engine.dispose()

    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
