"""Base provider interface and utilities for travel providers."""
from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional

from .cache import ProviderCache
from .models import SearchCriteria, TravelPackage
from .monitoring import ProviderMonitor
from .utils import (
    with_retry,
    RateLimiter,
    ProviderError,
    AuthenticationError,
    RateLimitError,
    ConnectionError,
    ValidationError,
    AvailabilityError
)

logger = logging.getLogger(__name__)


class BaseProvider(ABC):
    """Base class for all travel providers."""

    # Default rate limits - can be overridden by subclasses
    RATE_LIMIT_CALLS = 100  # calls
    RATE_LIMIT_PERIOD = 60  # seconds
    RATE_LIMIT_BURST = 120  # maximum burst

    def __init__(self, credentials: Dict[str, str]):
        """Initialize provider with credentials."""
        self.credentials = credentials
        self.cache = ProviderCache(self.__class__.__name__)
        self.monitor = ProviderMonitor(self.__class__.__name__)
        self.rate_limiter = RateLimiter(
            self.RATE_LIMIT_CALLS,
            self.RATE_LIMIT_PERIOD,
            self.RATE_LIMIT_BURST
        )
        self._validate_credentials()
        self._setup_session()

    @abstractmethod
    def _validate_credentials(self) -> None:
        """Validate provider credentials."""
        pass

    @abstractmethod
    def _setup_session(self) -> None:
        """Setup provider session."""
        pass

    async def _get_cached_token(self) -> Optional[Dict]:
        """Get cached authentication token."""
        start_time = self.monitor.start_operation("get_cached_token")
        try:
            token = await self.cache.get_auth_token()
            self.monitor.end_operation(
                "get_cached_token",
                start_time,
                success=True,
                cached=True if token else False
            )
            return token
        except Exception as e:
            self.monitor.end_operation(
                "get_cached_token",
                start_time,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise

    async def _cache_token(self, token_data: Dict) -> None:
        """Cache authentication token."""
        start_time = self.monitor.start_operation("cache_token")
        try:
            await self.cache.set_auth_token(token_data)
            self.monitor.end_operation("cache_token", start_time, success=True)
        except Exception as e:
            self.monitor.end_operation(
                "cache_token",
                start_time,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise

    @abstractmethod
    @with_retry()
    async def _search_provider(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """Perform actual search on provider."""
        pass

    async def search(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """Search for travel packages with caching and rate limiting."""
        start_time = self.monitor.start_operation("search")
        try:
            # Try to get from cache first
            cached_results = await self.cache.get_search_results(criteria)
            if cached_results:
                logger.info(f"Using cached search results for {criteria}")
                self.monitor.end_operation(
                    "search",
                    start_time,
                    success=True,
                    cached=True
                )
                return cached_results

            # Apply rate limiting
            async with self.rate_limiter:
                # If not in cache, perform actual search
                results = await self._search_provider(criteria)
                
                # Cache the results
                if results:
                    await self.cache.set_search_results(criteria, results)
                
                self.monitor.end_operation(
                    "search",
                    start_time,
                    success=True,
                    cached=False
                )
                return results
        except Exception as e:
            self.monitor.end_operation(
                "search",
                start_time,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            # Invalidate cache in case of error
            await self.invalidate_cache(criteria=criteria)
            raise

    @abstractmethod
    @with_retry()
    async def _get_package_details_provider(self, package_id: str) -> TravelPackage:
        """Get package details from provider."""
        pass

    async def get_package_details(self, package_id: str) -> TravelPackage:
        """Get detailed information for a specific package with caching and rate limiting."""
        start_time = self.monitor.start_operation("get_package_details")
        try:
            # Try to get from cache first
            cached_package = await self.cache.get_package_details(package_id)
            if cached_package:
                logger.info(f"Using cached package details for {package_id}")
                self.monitor.end_operation(
                    "get_package_details",
                    start_time,
                    success=True,
                    cached=True
                )
                return cached_package

            # Apply rate limiting
            async with self.rate_limiter:
                # If not in cache, get from provider
                package = await self._get_package_details_provider(package_id)
                
                # Cache the package details
                if package:
                    await self.cache.set_package_details(package)
                
                self.monitor.end_operation(
                    "get_package_details",
                    start_time,
                    success=True,
                    cached=False
                )
                return package
        except Exception as e:
            self.monitor.end_operation(
                "get_package_details",
                start_time,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            # Invalidate cache in case of error
            await self.invalidate_cache(package_id=package_id)
            raise

    @abstractmethod
    @with_retry(max_attempts=2, min_wait=0.5, max_wait=2)
    async def check_availability(self, package_id: str) -> bool:
        """Check if a package is still available.
        Note: This is not cached as availability needs to be real-time.
        Uses shorter retry parameters as this needs to be quick.
        """
        start_time = self.monitor.start_operation("check_availability")
        try:
            async with self.rate_limiter:
                result = await super().check_availability(package_id)
                self.monitor.end_operation(
                    "check_availability",
                    start_time,
                    success=True
                )
                return result
        except Exception as e:
            self.monitor.end_operation(
                "check_availability",
                start_time,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise

    async def get_status(self) -> Dict[str, Any]:
        """Get current provider status and metrics."""
        return self.monitor.get_status()

    async def invalidate_cache(
        self,
        criteria: Optional[SearchCriteria] = None,
        package_id: Optional[str] = None
    ) -> None:
        """Invalidate specific cache entries."""
        start_time = self.monitor.start_operation("invalidate_cache")
        try:
            if criteria:
                await self.cache.invalidate_search(criteria)
            if package_id:
                await self.cache.invalidate_package(package_id)
            self.monitor.end_operation("invalidate_cache", start_time, success=True)
        except Exception as e:
            self.monitor.end_operation(
                "invalidate_cache",
                start_time,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    @abstractmethod
    async def close(self):
        """Close provider session."""
        pass
