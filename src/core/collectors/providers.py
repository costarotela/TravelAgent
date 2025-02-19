"""Provider implementations for data collection."""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import PackageData, ProviderConfig, CollectionResult
from ..cache.smart_cache import SmartCache
from ..browsers.smart_browser import SmartBrowser
from ..monitoring import METRICS

logger = logging.getLogger(__name__)


class BaseProviderUpdater(ABC):
    """Base class for provider updaters."""

    def __init__(self, config: ProviderConfig, cache: Optional[SmartCache] = None):
        """Initialize provider updater.

        Args:
            config: Provider configuration
            cache: Optional cache instance
        """
        self.config = config
        self.cache = cache
        self.browser = SmartBrowser(headless=True)
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self.config.headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            )
        return self._session

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def fetch_data(self, destination: str) -> CollectionResult:
        """Fetch data from provider with retry logic.

        Args:
            destination: Destination to fetch data for

        Returns:
            Collection result with normalized data
        """
        start_time = datetime.utcnow()

        try:
            # Check cache first
            cache_key = f"{self.config.name}:{destination}"
            if self.cache:
                cached_data = self.cache.get(cache_key)
                if cached_data:
                    logger.info(f"Cache hit for {cache_key}")
                    return cached_data

            # Fetch and normalize data
            raw_data = await self._fetch_raw_data(destination)
            normalized_data = self._normalize_data(raw_data)

            # Create result
            result = CollectionResult(
                success=True,
                provider=self.config.name,
                destination=destination,
                packages=normalized_data,
                duration_ms=int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                ),
            )

            # Update cache
            if self.cache:
                self.cache.set(cache_key, result, ttl=self.config.cache_ttl)

            # Update metrics
            METRICS["collector_success"].labels(
                provider=self.config.name,
                destination=destination,
            ).inc()
            METRICS["collector_duration"].labels(
                provider=self.config.name,
                destination=destination,
            ).observe(result.duration_ms)

            return result

        except Exception as e:
            error_msg = f"Error fetching data from {self.config.name}: {str(e)}"
            logger.error(error_msg)

            # Update error metrics
            METRICS["collector_errors"].labels(
                provider=self.config.name,
                destination=destination,
                error_type=type(e).__name__,
            ).inc()

            return CollectionResult(
                success=False,
                provider=self.config.name,
                destination=destination,
                error=error_msg,
                duration_ms=int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                ),
            )

    @abstractmethod
    async def _fetch_raw_data(self, destination: str) -> List[dict]:
        """Fetch raw data from provider.

        Args:
            destination: Destination to fetch data for

        Returns:
            List of raw package data
        """
        pass

    @abstractmethod
    def _normalize_data(self, raw_data: List[dict]) -> List[PackageData]:
        """Normalize raw data to common format.

        Args:
            raw_data: Raw data from provider

        Returns:
            List of normalized package data
        """
        pass

    async def close(self):
        """Close resources."""
        if self._session and not self._session.closed:
            await self._session.close()
        await self.browser.close()
