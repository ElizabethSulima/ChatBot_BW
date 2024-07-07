import asyncio

from database import db


async def insert_admin():
    super_admin = {
        "user_id": 1116544590,
        "first_name": "Елизавета",
        "role": "admin",
        "bonuses": 0,
    }
    await db.test_collection.insert_one(super_admin)


if __name__ == "__main__":
    asyncio.run(insert_admin())
