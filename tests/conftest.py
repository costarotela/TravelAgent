"""Test configuration."""
import pytest
import asyncio
from src.core.database.base import db
from src.core.cache.redis_cache import cache


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_database():
    """Setup test database."""
    # Setup
    await db.init()
    
    yield
    
    # Cleanup
    await db.cleanup()


@pytest.fixture(autouse=True)
async def setup_cache():
    """Setup test cache."""
    # Setup
    await cache.init()
    
    yield
    
    # Cleanup
    await cache.cleanup()
