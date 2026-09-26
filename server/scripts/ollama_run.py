"""Find one CNF food for an ingredient name.

Exact alias returns immediately. Otherwise Laya chooses inside the foods
whose names contain the query words. A score of at least 0.75 saves that
wording as an alias. A lower score queues the top foods for the admin
screen and asks for a number in this console.

    docker compose exec server python scripts/ollama_run.py "beurre salé"
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.alias_link import link_alias
from app.database import AsyncSessionLocal, engine
from app.db_models.models import CatalogAliasReview
from app.ingredient_match import AUTO_ACCEPT, Food, match_ingredient
from app.seed_cnf import normalize_name


def emit(food: Food | None, confidence: float | None, reason: str = "none") -> None:
    if food is None:
        payload = {"match": None, "reason": reason, "confidence": confidence}
    else:
        payload = {"match": food.as_match(), "confidence": confidence}
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def ask_console(raw: str, confidence: float | None, foods: list[Food]) -> Food | None:
    shown = foods[:8]
    print(f"\n{raw!r} is not sure" + (f" (confidence {confidence:.2f})" if confidence is not None else ""))
    print(f"Auto-accept needs {AUTO_ACCEPT:.2f}. Pick a number, or press enter to leave it on the admin queue.")
    for index, food in enumerate(shown, start=1):
        score = "" if food.probability is None else f"  {food.probability:.0%}"
        print(f"  {index}. {food.name_en} / {food.name_fr}{score}")
    if not sys.stdin.isatty():
        try:
            line = sys.stdin.readline()
        except EOFError:
            return None
    else:
        try:
            line = input("> ")
        except EOFError:
            return None
    number = line.strip()
    if not number.isdigit():
        return None
    choice = int(number)
    if choice < 1 or choice > len(shown):
        return None
    return shown[choice - 1]


async def resolve(raw: str) -> None:
    result = await match_ingredient(raw)
    if result.status != "queued":
        emit(result.food, result.confidence)
        return
    chosen = ask_console(raw, result.confidence, result.candidates)
    if chosen is None:
        emit(None, result.confidence, "queued")
        return
    async with AsyncSessionLocal() as session:
        await link_alias(session, raw, chosen.id, chosen.name_en, chosen.name_fr)
        review = await session.scalar(
            select(CatalogAliasReview).where(
                CatalogAliasReview.normalized == normalize_name(raw)
            )
        )
        if review is not None and review.status != "resolved":
            review.status = "resolved"
            review.food_id = chosen.id
            await session.commit()
    emit(chosen, result.confidence)


async def _main(raw: str) -> None:
    try:
        await resolve(raw)
    finally:
        await engine.dispose()


def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        raise SystemExit('usage: python scripts/ollama_run.py "ingredient"')
    asyncio.run(_main(sys.argv[1]))


if __name__ == "__main__":
    main()
