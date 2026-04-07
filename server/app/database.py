# app/database.py
import os
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.engine import URL

raw_url = os.getenv("DATABASE_URL")

if raw_url:
    if raw_url.startswith("postgres://"):
        db_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw_url.startswith("postgresql://"):
        db_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        db_url = raw_url
else:
    # Fallback construction
    user = os.getenv("DB_USER")
    pw = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "timescale")
    port = os.getenv("DB_PORT", "6667")
    name = os.getenv("DB_NAME", "db")
    db_url = f"postgresql+asyncpg://{user}:{pw}@{host}:{port}/{name}"

engine = create_async_engine(
    db_url,
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            # Context manager handles close() automatically
            pass
