"""Seed script — creates the first admin member.

Usage (inside Docker):
  sudo docker exec <PROJECT_NAME>-backend python seed.py
"""
import asyncio
from sqlalchemy import select
from app.database import async_session, engine, Base
from app.models import Member
from app.services.auth import hash_password


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        existing = await db.execute(select(Member).where(Member.username == "admin"))
        if existing.scalar_one_or_none():
            print("Admin user already exists.")
            return

        admin = Member(
            username="admin",
            password_hash=hash_password("admin123"),
            name="Administrator",
            is_admin=True,
        )
        db.add(admin)
        await db.commit()
        print("Created admin (username=admin, password=admin123). CHANGE THIS IN PRODUCTION.")


if __name__ == "__main__":
    asyncio.run(seed())
