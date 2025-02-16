"""Redis cache implementation."""
import json
from typing import Any, Optional
from redis import Redis
from src.core.config.settings import settings

class RedisCache:
    """Redis cache system for improved performance."""
    
    def __init__(self):
        self.redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = self.redis.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = None
    ) -> bool:
        """Set value in cache with TTL."""
        try:
            return self.redis.set(
                key,
                json.dumps(value),
                ex=ttl or settings.CACHE_TTL
            )
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    async def clear(self) -> bool:
        """Clear all cache."""
        try:
            return self.redis.flushdb()
        except Exception as e:
            print(f"Cache clear error: {e}")
            return False

# Global cache instance
cache = RedisCache()
