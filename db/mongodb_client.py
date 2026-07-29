from pymongo import MongoClient
from app.core.config import settings

client = MongoClient(
    settings.MONGO_URL,
    serverSelectionTimeoutMS=3000,
    socketTimeoutMS=5000,
    connectTimeoutMS=3000
)
mongo_db = client.get_database("gestor")