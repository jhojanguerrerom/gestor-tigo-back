from app.repositories.log_repository import LogRepository

class LogService:
    def __init__(self):
        self.repo = LogRepository()

    def add_log(self, level: str, message: str, meta: dict = None):
        return self.repo.insert(level=level, message=message, meta=meta)
