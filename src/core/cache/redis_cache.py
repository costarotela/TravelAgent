"""Redis cache implementation."""

import json
import aioredis
from typing import Any, Optional


class RedisCache:
    """Redis cache implementation."""

    def __init__(self):
        """Initialize Redis cache."""
        self._redis = None

    async def init(self):
        """Initialize Redis connection."""
        if not self._redis:
            self._redis = await aioredis.create_redis_pool("redis://localhost")

    async def cleanup(self):
        """Cleanup Redis connection."""
        if self._redis:
            self._redis.close()
            await self._redis.wait_closed()
            self._redis = None

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self._redis:
            return None

        value = await self._redis.get(key)
        if not value:
            return None

        return json.loads(value)

    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            expire: Optional expiration in seconds
        """
        if not self._redis:
            return

        await self._redis.set(key, json.dumps(value), expire=expire)

    async def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key to delete
        """
        if not self._redis:
            return

        await self._redis.delete(key)


# Global cache instance
cache = RedisCache()
