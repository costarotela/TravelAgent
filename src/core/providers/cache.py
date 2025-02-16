"""Cache implementation for travel providers."""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import redis

from .models import SearchCriteria, TravelPackage

logger = logging.getLogger(__name__)

class ProviderCache:
    """Cache implementation for provider data."""

    def __init__(self, provider_name: str):
        """Initialize cache with Redis connection."""
        self.provider_name = provider_name
        self.redis = redis.Redis(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True
        )
        self.default_ttl = timedelta(minutes=30)

    def _get_auth_key(self) -> str:
        """Get Redis key for auth token."""
        return f"{self.provider_name}:auth_token"

    def _get_search_key(self, criteria: SearchCriteria) -> str:
        """Get Redis key for search results."""
        return f"{self.provider_name}:search:{criteria.json()}"

    def _get_package_key(self, package_id: str) -> str:
        """Get Redis key for package details."""
        return f"{self.provider_name}:package:{package_id}"

    async def get_auth_token(self) -> Optional[Dict]:
        """Get cached authentication token."""
        token_data = self.redis.get(self._get_auth_key())
        if token_data:
            return json.loads(token_data)
        return None

    async def set_auth_token(self, token_data: Dict, ttl: Optional[timedelta] = None) -> None:
        """Cache authentication token."""
        self.redis.setex(
            self._get_auth_key(),
            ttl or self.default_ttl,
            json.dumps(token_data)
        )

    async def get_search_results(self, criteria: SearchCriteria) -> Optional[List[TravelPackage]]:
        """Get cached search results."""
        results_data = self.redis.get(self._get_search_key(criteria))
        if results_data:
            return [
                TravelPackage(**package_data)
                for package_data in json.loads(results_data)
            ]
        return None

    async def set_search_results(
        self,
        criteria: SearchCriteria,
        results: List[TravelPackage],
        ttl: Optional[timedelta] = None
    ) -> None:
        """Cache search results."""
        self.redis.setex(
            self._get_search_key(criteria),
            ttl or self.default_ttl,
            json.dumps([package.dict() for package in results])
        )

    async def get_package_details(self, package_id: str) -> Optional[TravelPackage]:
        """Get cached package details."""
        package_data = self.redis.get(self._get_package_key(package_id))
        if package_data:
            return TravelPackage(**json.loads(package_data))
        return None

    async def set_package_details(
        self,
        package: TravelPackage,
        ttl: Optional[timedelta] = None
    ) -> None:
        """Cache package details."""
        self.redis.setex(
            self._get_package_key(package.id),
            ttl or self.default_ttl,
            json.dumps(package.dict())
        )

    async def invalidate_search(self, criteria: SearchCriteria) -> None:
        """Invalidate cached search results."""
        self.redis.delete(self._get_search_key(criteria))

    async def invalidate_package(self, package_id: str) -> None:
        """Invalidate cached package details."""
        self.redis.delete(self._get_package_key(package_id))

    async def invalidate_all(self) -> None:
        """Invalidate all cached data for this provider."""
        pattern = f"{self.provider_name}:*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)
