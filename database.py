import motor.motor_asyncio

from settings import settings


client = motor.motor_asyncio.AsyncIOMotorClient(settings.db_url)
db = client[settings.DB_NAME]
collection = db[settings.DB_COLLECTION]
