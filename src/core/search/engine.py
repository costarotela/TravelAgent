"""Search engine for travel packages across multiple providers."""
import asyncio
import logging
from typing import Dict, List, Optional, Type

from ..providers import (
    AeroProvider,
    BaseProvider,
    DespegarProvider,
    OlaProvider,
    SearchCriteria,
    TravelPackage
)

logger = logging.getLogger(__name__)


class SearchEngine:
    """Search engine that coordinates searches across multiple providers."""

    def __init__(self, provider_credentials: Dict[str, Dict[str, str]]):
        """Initialize search engine with provider credentials.
        
        Args:
            provider_credentials: Dictionary mapping provider names to their credentials
                Example: {
                    "OLA": {"api_key": "...", "api_secret": "..."},
                    "AERO": {"client_id": "...", "client_secret": "..."},
                    "DESPEGAR": {"api_key": "...", "affiliate_id": "..."}
                }
        """
        self.provider_credentials = provider_credentials
        self.provider_classes = {
            "OLA": OlaProvider,
            "AERO": AeroProvider,
            "DESPEGAR": DespegarProvider
        }
        self._validate_credentials()

    def _validate_credentials(self) -> None:
        """Validate that credentials are provided for all providers."""
        for provider_name, provider_class in self.provider_classes.items():
            if provider_name not in self.provider_credentials:
                raise ValueError(f"Missing credentials for provider: {provider_name}")

    async def search(
        self,
        criteria: SearchCriteria,
        providers: Optional[List[str]] = None,
        timeout: int = 30
    ) -> List[TravelPackage]:
        """Search for travel packages across all or specified providers.
        
        Args:
            criteria: Search criteria for the packages
            providers: Optional list of provider names to search. If None, search all
            timeout: Maximum time to wait for responses in seconds
        
        Returns:
            List of travel packages from all providers
        """
        if providers is None:
            providers = list(self.provider_classes.keys())
        else:
            providers = [p.upper() for p in providers]
            invalid_providers = set(providers) - set(self.provider_classes.keys())
            if invalid_providers:
                raise ValueError(f"Invalid providers: {invalid_providers}")

        search_tasks = []
        for provider_name in providers:
            provider_class = self.provider_classes[provider_name]
            credentials = self.provider_credentials[provider_name]
            search_tasks.append(
                self._search_provider(provider_class, credentials, criteria)
            )

        try:
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
        except asyncio.TimeoutError:
            logger.error("Search timeout exceeded")
            raise TimeoutError("Search took too long to complete")

        packages = []
        for provider_name, result in zip(providers, results):
            if isinstance(result, Exception):
                logger.error(f"Error searching {provider_name}: {result}")
                continue
            packages.extend(result)

        return self._sort_packages(packages)

    async def _search_provider(
        self,
        provider_class: Type[BaseProvider],
        credentials: Dict[str, str],
        criteria: SearchCriteria
    ) -> List[TravelPackage]:
        """Search a single provider for travel packages.
        
        Args:
            provider_class: The provider class to instantiate
            credentials: Credentials for the provider
            criteria: Search criteria
        
        Returns:
            List of travel packages from the provider
        """
        try:
            async with provider_class(credentials) as provider:
                return await provider.search(criteria)
        except Exception as e:
            logger.error(f"Error searching with {provider_class.__name__}: {e}")
            raise

    def _sort_packages(self, packages: List[TravelPackage]) -> List[TravelPackage]:
        """Sort packages by price and availability.
        
        Args:
            packages: List of packages to sort
        
        Returns:
            Sorted list of packages
        """
        return sorted(
            packages,
            key=lambda x: (not x.availability, x.price)
        )
