"""One-shot seed: copy match-checker rows from the legacy SQLite DB into Postgres.

Run from the server container:

    docker compose exec server python -m app.sqlitetopostgres
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import func, select

# `python app/sqlitetopostgres.py` puts this file's directory on sys.path,
# not /code, so `import app` would fail without this.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import AsyncSessionLocal
from app.db_models.models import MatchChecker

SQLITE_PATH = ROOT / "db.sqlite3"


def _parse_json_list(raw: str | None):
    if not raw:
        return []
    value = json.loads(raw)
    return value if isinstance(value, list) else []


def load_sqlite_rows() -> list[MatchChecker]:
    if not SQLITE_PATH.exists():
        raise FileNotFoundError(f"SQLite seed DB not found at {SQLITE_PATH}")

    conn = sqlite3.connect(SQLITE_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT title, avoid, afinities, matchs FROM api_ingredient")
        items = []
        for title, avoid, affinities, matches in cursor.fetchall():
            items.append(
                MatchChecker(
                    title=title,
                    avoid=_parse_json_list(avoid),
                    affinities=_parse_json_list(affinities),
                    matches=_parse_json_list(matches),
                )
            )
        return items
    finally:
        conn.close()


async def migrate() -> None:
    items = load_sqlite_rows()
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(func.count()).select_from(MatchChecker))
        if existing:
            print(f"match_checker already has {existing} rows; skipping import.")
            return

        db.add_all(items)
        await db.commit()
        print(f"Migrated {len(items)} ingredients into match_checker.")


if __name__ == "__main__":
    asyncio.run(migrate())
