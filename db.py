from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

client = AsyncIOMotorClient(settings.mongo_uri)
master_db = client[settings.master_db_name]

organizations_collection = master_db["organizations"]
admins_collection = master_db["admins"]
