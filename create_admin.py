import asyncio
from datetime import datetime

from database import db
from settings import settings


async def insert_admin():
    super_admin = {
        "user_id": settings.ADMIN_ID,
        "first_name": settings.ADMIN_NAME,
        "role": "super_admin",
        "bonuses": 0,
        "time_bonuses": datetime.now().date().strftime("%d:%m:%Y"),
    }
    await db[settings.DB_COLLECTION].insert_one(super_admin)


if __name__ == "__main__":
    asyncio.run(insert_admin())
