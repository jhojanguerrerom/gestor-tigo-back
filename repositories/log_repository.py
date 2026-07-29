from app.db.mongodb_client import mongo_db
import datetime

class LogRepository:
    def __init__(self):
        self.collection = mongo_db.get_collection("logs")

    def insert(self, level: str, message: str, meta: dict = None):
        doc = {"level": level, "message": message, "meta": meta or {}, "ts": datetime.datetime.utcnow()}
        return self.collection.insert_one(doc).inserted_id

    def list_recent(self, limit: int = 20):
        return list(self.collection.find().sort("ts", -1).limit(limit))
