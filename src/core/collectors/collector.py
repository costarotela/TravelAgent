"""Main data collector implementation."""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
from prometheus_client import Counter, Histogram

from .models import PackageData, ProviderConfig, CollectionResult
from .providers import BaseProviderUpdater
from ..cache.smart_cache import SmartCache
from ..monitoring import METRICS

logger = logging.getLogger(__name__)

# Initialize metrics
METRICS["collector_success"] = Counter(
    "collector_success_total",
    "Successful data collections",
    ["provider", "destination"],
)
METRICS["collector_errors"] = Counter(
    "collector_errors_total",
    "Failed data collections",
    ["provider", "destination", "error_type"],
)
METRICS["collector_duration"] = Histogram(
    "collector_duration_seconds",
    "Time taken for data collection",
    ["provider", "destination"],
)


class DataCollector:
    """Coordinator for collecting data from multiple providers."""

    def __init__(
        self,
        provider_updaters: List[BaseProviderUpdater],
        cache: Optional[SmartCache] = None,
    ):
        """Initialize data collector.

        Args:
            provider_updaters: List of provider updaters
            cache: Optional cache instance
        """
        self.provider_updaters = provider_updaters
        self.cache = cache
        self._collection_tasks: Dict[str, asyncio.Task] = {}

    async def collect_data(self, destination: str) -> List[CollectionResult]:
        """Collect data from all providers for a destination.

        Args:
            destination: Destination to collect data for

        Returns:
            List of collection results
        """
        # Create tasks for each provider
        tasks = []
        for updater in self.provider_updaters:
            task = asyncio.create_task(
                self._collect_from_provider(updater, destination)
            )
            self._collection_tasks[updater.config.name] = task
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        collection_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error in collection task: {str(result)}")
                # Create error result
                collection_results.append(
                    CollectionResult(
                        success=False,
                        provider="unknown",
                        destination=destination,
                        error=str(result),
                        duration_ms=0,
                    )
                )
            else:
                collection_results.append(result)

        return collection_results

    async def _collect_from_provider(
        self, updater: BaseProviderUpdater, destination: str
    ) -> CollectionResult:
        """Collect data from a single provider.

        Args:
            updater: Provider updater
            destination: Destination to collect data for

        Returns:
            Collection result
        """
        try:
            # Apply rate limiting
            await asyncio.sleep(updater.config.rate_limit_interval)

            # Fetch data
            result = await updater.fetch_data(destination)

            # Log result
            if result.success:
                logger.info(
                    f"Successfully collected {len(result.packages)} packages from "
                    f"{updater.config.name} for {destination}"
                )
            else:
                logger.error(
                    f"Failed to collect data from {updater.config.name}: {result.error}"
                )

            return result

        except Exception as e:
            logger.error(f"Error collecting from {updater.config.name}: {str(e)}")
            raise

    def get_active_tasks(self) -> Dict[str, bool]:
        """Get status of active collection tasks.

        Returns:
            Dictionary mapping provider names to task done status
        """
        return {name: task.done() for name, task in self._collection_tasks.items()}

    async def close(self):
        """Close all provider updaters."""
        for updater in self.provider_updaters:
            await updater.close()
