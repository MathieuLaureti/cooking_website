"""Resolve one typed ingredient name to a CNF food or a pending alias review."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, replace

from sqlalchemy import select

from app.alias_link import link_alias, queue_review
from app.database import AsyncSessionLocal
from app.db_models.models import CatalogAlias, CatalogFood
from app.seed_cnf import normalize_name

BASE = "http://192.168.2.99:11435"
MODEL = "laya"
SOURCE = "cnf"
LEAF = 20
MIN_CHILD = 8
MAX_DEPTH = 4
CLOSE_GAP = 0.08
AUTO_ACCEPT = 0.75
CHOICE_CAP = 254
ATTRIBUTE_TOKENS = {"raw", "cooked", "salted", "canned", "dried"}
NONE = "none"
OTHER = "other"
STOP_WORDS = {"de", "du", "des", "la", "le", "les", "un", "une", "au", "aux", "en", "et", "of", "and", "the"}


@dataclass(frozen=True)
class Food:
    id: int
    name_en: str
    name_fr: str
    group_code: str
    group_en: str
    group_fr: str
    parts: tuple[str, ...]
    probability: float | None = None

    def as_match(self) -> dict:
        return {
            "id": self.id,
            "name_en": self.name_en,
            "name_fr": self.name_fr,
            "group_en": self.group_en,
        }


def token_forms(state: str) -> list[set[str]]:
    forms: list[set[str]] = []
    for token in normalize_name(state).split():
        if token in STOP_WORDS or len(token) <= 1:
            continue
        options = {token}
        if len(token) > 3 and token.endswith("s"):
            options.add(token[:-1])
        if len(token) > 4 and token.endswith("es"):
            options.add(token[:-2])
        forms.append(options)
    return forms


def food_words(food: Food) -> set[str]:
    return set(normalize_name(food.name_en).split()) | set(normalize_name(food.name_fr).split())


def covers(words: set[str], forms: list[set[str]]) -> bool:
    return all(words & options for options in forms)


def focus_criteria(state: str, criteria: dict[str, str]) -> dict[str, str]:
    forms = token_forms(state)
    if not forms:
        return criteria
    scored: list[tuple[int, str]] = []
    for key, text in criteria.items():
        if key in {NONE, OTHER}:
            continue
        text_words = set(normalize_name(text).split())
        scored.append((sum(1 for options in forms if text_words & options), key))
    if not scored:
        return criteria
    best = max(score for score, _key in scored)
    if best == 0:
        return criteria
    winners = {key for score, key in scored if score == best}
    if len(winners) == len(scored):
        return criteria
    focused = {key: criteria[key] for key in criteria if key in winners}
    focused[NONE] = criteria[NONE]
    return focused


def decide(state: str, instructions: str, criteria: dict[str, str]) -> tuple[str | None, float | None, dict[str, float]]:
    criteria = focus_criteria(state, criteria)
    body = json.dumps(
        {
            "model": MODEL,
            "state": state,
            "questions": {
                "pick": {
                    "type": "choice",
                    "instructions": instructions,
                    "criteria": criteria,
                }
            },
        }
    ).encode()
    request = urllib.request.Request(
        f"{BASE}/api/decide",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"{exc.code} {exc.reason}: {detail}") from exc
    answer = data["answers"]["pick"]
    choice = answer.get("choice")
    raw_confidence = answer.get("confidence")
    confidence = float(raw_confidence) if raw_confidence is not None else None
    probabilities = {key: float(value) for key, value in (answer.get("probabilities") or {}).items()}
    ranked = sorted(probabilities.values(), reverse=True)
    close = len(ranked) >= 2 and ranked[0] - ranked[1] < CLOSE_GAP
    if choice == NONE or close or choice not in criteria:
        return None, confidence, probabilities
    return choice, confidence, probabilities


def category_index(foods: list[Food], start: int) -> int | None:
    index = start
    while index < 8:
        tokens = {
            food.parts[index].strip()
            for food in foods
            if index < len(food.parts) and food.parts[index].strip().lower() not in ATTRIBUTE_TOKENS
        }
        if len(tokens) >= 2:
            return index
        index += 1
    return None


def bucket_token(food: Food, index: int) -> str | None:
    if index >= len(food.parts):
        return None
    token = food.parts[index].strip()
    if token.lower() in ATTRIBUTE_TOKENS:
        return None
    return token


def hint_tokens(foods: list[Food], index: int) -> str:
    counts: dict[str, int] = defaultdict(int)
    for food in foods:
        taken = 0
        for part in food.parts[index + 1 :]:
            token = part.strip()
            if token.lower() in ATTRIBUTE_TOKENS:
                continue
            counts[token] += 1
            taken += 1
            if taken >= 2:
                break
    ranked = sorted(counts, key=lambda token: counts[token], reverse=True)[:6]
    return ", ".join(ranked)


def describe_bucket(token: str, foods: list[Food], index: int, state: str) -> str:
    query = set(normalize_name(state).split())

    def score(food: Food) -> int:
        words = set(normalize_name(food.name_en).split()) | set(normalize_name(food.name_fr).split())
        return len(query & words)

    example = max(foods, key=score)
    hints = hint_tokens(foods, index)
    extra = f" ({token}; {hints})" if hints else f" ({token})"
    return f"{example.name_en} / {example.name_fr}{extra}"


def narrow(state: str, foods: list[Food], start: int, depth: int) -> tuple[Food | None, float | None, list[Food]]:
    if not foods:
        return None, None, []
    if len(foods) <= LEAF or depth >= MAX_DEPTH:
        return choose_food(state, foods)
    index = category_index(foods, start)
    if index is None:
        return choose_food(state, foods)
    buckets: dict[str | None, list[Food]] = defaultdict(list)
    for food in foods:
        buckets[bucket_token(food, index)].append(food)
    promoted = {token: rows for token, rows in buckets.items() if token and len(rows) >= MIN_CHILD}
    if not promoted:
        return choose_food(state, foods)
    rest = [food for token, rows in buckets.items() if token not in promoted for food in rows]
    criteria = {
        token: describe_bucket(token, rows, index, state) for token, rows in promoted.items()
    }
    if rest:
        criteria[OTHER] = "Other foods in this group"
    criteria[NONE] = "Not in this list"
    choice, confidence, _probabilities = decide(state, "Which category contains this ingredient?", criteria)
    if choice is None or confidence is None or confidence < AUTO_ACCEPT:
        return None, confidence, foods
    if choice == OTHER:
        return narrow(state, rest, index + 1, depth + 1)
    return narrow(state, promoted[choice], index + 1, depth + 1)


def choose_food(state: str, foods: list[Food]) -> tuple[Food | None, float | None, list[Food]]:
    if len(foods) == 1:
        return foods[0], 1.0, foods
    ordered = sorted(foods, key=lambda food: food.name_en)[:CHOICE_CAP]
    criteria = {str(food.id): f"{food.name_en} / {food.name_fr}" for food in ordered}
    criteria[NONE] = "Not in this list"
    choice, confidence, probabilities = decide(state, "Which food is this ingredient?", criteria)
    ranked = sorted(
        (replace(food, probability=probabilities.get(str(food.id))) for food in ordered),
        key=lambda food: food.probability or 0.0,
        reverse=True,
    )
    if choice and confidence is not None and confidence >= AUTO_ACCEPT:
        return next(food for food in ordered if str(food.id) == choice), confidence, ranked
    return None, confidence, ranked


def choose_group(state: str, foods: list[Food]) -> tuple[Food | None, float | None, list[Food]]:
    groups: dict[str, tuple[str, str]] = {}
    for food in foods:
        groups.setdefault(food.group_code, (food.group_en, food.group_fr))
    if len(groups) == 1:
        return narrow(state, foods, 0, 1)
    criteria = {code: f"{en} / {fr}" for code, (en, fr) in sorted(groups.items(), key=lambda item: item[1][0])}
    criteria[NONE] = "Not in this list"
    choice, confidence, _probabilities = decide(state, "Which food group contains this ingredient?", criteria)
    if choice is None or confidence is None or confidence < AUTO_ACCEPT:
        return None, confidence, foods
    chosen = [food for food in foods if food.group_code == choice]
    return narrow(state, chosen, 0, 1)


async def alias_food(name: str) -> Food | None:
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                select(
                    CatalogFood.id,
                    CatalogFood.name_en,
                    CatalogFood.name_fr,
                    CatalogFood.group_code,
                    CatalogFood.group_en,
                    CatalogFood.group_fr,
                )
                .join(CatalogAlias, CatalogAlias.food_id == CatalogFood.id)
                .where(CatalogAlias.normalized == name, CatalogFood.source == SOURCE)
            )
        ).first()
    if row is None:
        return None
    return Food(
        id=row.id,
        name_en=row.name_en,
        name_fr=row.name_fr,
        group_code=row.group_code or "",
        group_en=row.group_en or "",
        group_fr=row.group_fr or "",
        parts=tuple(part.strip() for part in row.name_en.split(",") if part.strip()),
    )


async def load_foods() -> list[Food]:
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(
                    CatalogFood.id,
                    CatalogFood.name_en,
                    CatalogFood.name_fr,
                    CatalogFood.group_code,
                    CatalogFood.group_en,
                    CatalogFood.group_fr,
                ).where(CatalogFood.source == SOURCE)
            )
        ).all()
    return [
        Food(
            id=row.id,
            name_en=row.name_en,
            name_fr=row.name_fr,
            group_code=row.group_code or "",
            group_en=row.group_en or "",
            group_fr=row.group_fr or "",
            parts=tuple(part.strip() for part in row.name_en.split(",") if part.strip()),
        )
        for row in rows
    ]


def candidate_payload(foods: list[Food], limit: int = 8) -> list[dict]:
    return [
        {
            "food_id": food.id,
            "name_en": food.name_en,
            "name_fr": food.name_fr,
            "probability": food.probability,
        }
        for food in foods[:limit]
    ]


@dataclass
class MatchResult:
    status: str
    food: Food | None
    confidence: float | None
    candidates: list[Food]


async def match_ingredient(raw: str) -> MatchResult:
    normalized = normalize_name(raw)
    if not normalized:
        return MatchResult("none", None, None, [])
    hit = await alias_food(normalized)
    if hit is not None:
        return MatchResult("match", hit, 1.0, [])
    forms = token_forms(raw)
    foods = [food for food in await load_foods() if forms and covers(food_words(food), forms)]
    if not foods:
        return MatchResult("none", None, None, [])
    if len(foods) == 1:
        async with AsyncSessionLocal() as session:
            await link_alias(session, raw, foods[0].id, foods[0].name_en, foods[0].name_fr)
        return MatchResult("match", foods[0], 1.0, [])
    food, confidence, candidates = choose_group(raw.strip(), foods)
    if food is not None and confidence is not None and confidence >= AUTO_ACCEPT:
        async with AsyncSessionLocal() as session:
            await link_alias(session, raw, food.id, food.name_en, food.name_fr)
        return MatchResult("match", food, confidence, [])
    shortlist = candidates or foods
    async with AsyncSessionLocal() as session:
        await queue_review(session, raw, confidence, candidate_payload(shortlist))
    return MatchResult("queued", None, confidence, shortlist)
