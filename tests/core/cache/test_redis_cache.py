"""Tests for Redis cache."""
import pytest
from src.core.cache.redis_cache import cache


@pytest.mark.asyncio
async def test_cache_operations():
    """Test basic cache operations."""
    # Test set and get
    await cache.set("test_key", {"value": 123})
    value = await cache.get("test_key")
    assert value == {"value": 123}
    
    # Test delete
    await cache.delete("test_key")
    value = await cache.get("test_key")
    assert value is None
    
    # Test expiration
    await cache.set("expire_key", "test", expire=1)
    value = await cache.get("expire_key")
    assert value == "test"
    
    # Wait for expiration
    import asyncio
    await asyncio.sleep(2)
    value = await cache.get("expire_key")
    assert value is None
