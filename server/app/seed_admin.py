import os

from sqlalchemy import func, select

from app.auth import hash_password
from app.database import AsyncSessionLocal
from app.db_models.models import User


async def seed_admin_if_needed() -> None:
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    if not username or not password:
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count()).select_from(User))
        count = result.scalar_one()
        if count > 0:
            return

        db.add(
            User(
                username=username,
                password_hash=hash_password(password),
                role="admin",
            )
        )
        await db.commit()
