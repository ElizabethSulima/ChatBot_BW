import motor.motor_asyncio


client = motor.motor_asyncio.AsyncIOMotorClient(
    "mongodb://postgres:postgres@localhost:27017/"
)
db = client["test_database"]
collection = db["test_collection"]
