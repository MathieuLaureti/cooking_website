"""Shared pytest fixtures for the FastAPI server."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator, Callable
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

_SERVER_ROOT = Path(__file__).resolve().parents[1]

# Apply before any `app` import (database URL is read at import time).
os.environ.setdefault("JWT_SECRET", "pytest-jwt-secret")
os.environ.setdefault("DISABLE_IMPORT_WORKER", "1")
os.environ.setdefault("SQLALCHEMY_POOL_NULL", "1")
if url := os.environ.get("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = url


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture(scope="session")
def postgres_available() -> bool:
    import psycopg

    if os.getenv("DATABASE_URL"):
        try:
            conn = psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=3)
            conn.close()
            return True
        except Exception:
            return False
    user = os.getenv("DB_USER")
    if not user:
        return False
    try:
        conn = psycopg.connect(
            dbname=os.getenv("DB_NAME", "cooking_dev"),
            user=user,
            password=os.getenv("DB_PASSWORD", ""),
            host=os.getenv("DB_HOST", "192.168.2.99"),
            port=os.getenv("DB_PORT", "5432"),
            connect_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def migrated_db(postgres_available: bool) -> None:
    if not postgres_available:
        pytest.skip("Postgres not reachable (set DB_* or TEST_DATABASE_URL)")
    import subprocess

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=_SERVER_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"alembic upgrade failed: {result.stderr or result.stdout}")


@pytest.fixture
async def db_session(migrated_db: None) -> AsyncIterator[AsyncSession]:
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def test_users(db_session: AsyncSession) -> dict[str, object]:
    from app.auth import hash_password
    from app.db_models.models import User

    tag = uuid.uuid4().hex[:10]
    admin = User(
        username=f"t_admin_{tag}",
        password_hash=hash_password("adminpass"),
        role="admin",
    )
    regular = User(
        username=f"t_user_{tag}",
        password_hash=hash_password("userpass"),
        role="user",
    )
    db_session.add_all([admin, regular])
    await db_session.commit()
    await db_session.refresh(admin)
    await db_session.refresh(regular)
    return {"admin": admin, "user": regular}


@pytest.fixture
def make_token() -> Callable[..., str]:
    from app.auth import create_access_token

    def _factory(user) -> str:
        return create_access_token(user.id, user.username, user.role)

    return _factory


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
