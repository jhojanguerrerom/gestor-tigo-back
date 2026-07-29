from functools import wraps
import json
from app.core.redis_cache import redis_client
import asyncio

def cache(ttl=60):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"cache:{func.__name__}:{json.dumps({'args':args,'kwargs':kwargs}, default=str)}"
            try:
                cached = await redis_client.get(key)
            except Exception:
                cached = None
            if cached:
                return json.loads(cached)
            result = await func(*args, **kwargs)
            try:
                await redis_client.setex(key, ttl, json.dumps(result, default=str))
            except Exception:
                pass
            return result
        return wrapper
    return decorator
