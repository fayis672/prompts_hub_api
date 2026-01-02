import redis
from app.core.config import settings
import json
from typing import Optional, Any

class RedisService:
    def __init__(self):
        self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    def get(self, key: str) -> Optional[Any]:
        value = self.client.get(key)
        if value:
            return json.loads(value)
        return None

    def set(self, key: str, value: Any, expire: int = 3600):
        self.client.set(key, json.dumps(value), ex=expire)
    
    def delete(self, key: str):
        self.client.delete(key)

redis_service = RedisService()
