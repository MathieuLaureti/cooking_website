import asyncio
import os

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth import hash_password
from app.database import AsyncSessionLocal
from app.db_models.models import User


async def ensure_admin_user() -> None:
    """Create or update the bootstrap admin from ADMIN_USERNAME / ADMIN_PASSWORD."""
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    if not username or not password:
        return

    password_hash = hash_password(password)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user:
            user.password_hash = password_hash
            user.role = "admin"
        else:
            db.add(
                User(
                    username=username,
                    password_hash=password_hash,
                    role="admin",
                )
            )

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()


# Kept for backwards compatibility if anything still imports it.
async def seed_admin_if_needed() -> None:
    await ensure_admin_user()


def main() -> None:
    asyncio.run(ensure_admin_user())


if __name__ == "__main__":
    main()
