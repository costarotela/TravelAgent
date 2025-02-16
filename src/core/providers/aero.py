"""Aero provider implementation."""
import logging
from typing import Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from .base import BaseProvider
from .models import SearchCriteria, TravelPackage
from .utils import (
    AuthenticationError,
    ConnectionError,
    ProviderError,
    RateLimitError,
    ValidationError,
    with_retry
)

logger = logging.getLogger(__name__)


class AeroProvider(BaseProvider):
    """Provider implementation for Aero."""

    BASE_URL = "https://api.aero.com"
    AUTH_ENDPOINT = "/auth/token"
    SEARCH_ENDPOINT = "/flights/search"
    DETAILS_ENDPOINT = "/flights/details"

    # Configuración específica de rate limits para Aero
    RATE_LIMIT_CALLS = 150  # Aero permite más llamadas
    RATE_LIMIT_PERIOD = 60  # por minuto
    RATE_LIMIT_BURST = 180  # con un burst mayor

    def _validate_credentials(self) -> None:
        """Validate Aero credentials."""
        required_fields = ["client_id", "client_secret"]
        for field in required_fields:
            if field not in self.credentials:
                raise ValidationError(
                    f"Missing required credential: {field}",
                    "AERO"
                )

    async def _setup_session(self) -> None:
        """Setup Aero session with OAuth authentication."""
        self._session = aiohttp.ClientSession(
            base_url=self.BASE_URL,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        await self._authenticate()

    @with_retry(max_attempts=3, min_wait=2, max_wait=15)
    async def _authenticate(self) -> None:
        """Authenticate with Aero API using OAuth."""
        # Try to get cached token first
        token_data = await self._get_cached_token()
        if token_data:
            self._session.headers.update({
                "Authorization": f"Bearer {token_data['access_token']}",
                "Content-Type": "application/json"
            })
            return

        try:
            auth_data = {
                "grant_type": "client_credentials",
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"]
            }
            async with self._session.post(self.AUTH_ENDPOINT, json=auth_data) as response:
                if response.status == 401:
                    raise AuthenticationError(
                        "Invalid credentials",
                        "AERO"
                    )
                elif response.status == 429:
                    raise RateLimitError(
                        "Authentication rate limit exceeded",
                        "AERO"
                    )
                
                response.raise_for_status()
                token_data = await response.json()
                
                self._session.headers.update({
                    "Authorization": f"Bearer {token_data['access_token']}",
                    "Content-Type": "application/json"
                })
                # Cache the token
                await self._cache_token(token_data)
        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"Failed to authenticate with Aero: {str(e)}",
                "AERO",
                original_error=e
            )

    async def search(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """Search for flights in Aero."""
        try:
            return await self._search_provider(criteria)
        except Exception as e:
            logger.error(f"Unexpected error during Aero search: {e}")
            raise

    async def _search_provider(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """Perform actual search on Aero provider."""
        try:
            search_params = self._build_search_params(criteria)
            async with self._session.post(self.SEARCH_ENDPOINT, json=search_params) as response:
                if response.status == 401:
                    await self._authenticate()
                    return await self._search_provider(criteria)
                elif response.status == 400:
                    data = await response.json()
                    raise ValidationError(
                        f"Invalid search parameters: {data.get('message', 'Unknown error')}",
                        "AERO"
                    )
                elif response.status == 429:
                    raise RateLimitError(
                        "Search rate limit exceeded",
                        "AERO"
                    )
                
                response.raise_for_status()
                data = await response.json()
                return [self._parse_package(pkg) for pkg in data["flights"]]
        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"Failed to search Aero flights: {str(e)}",
                "AERO",
                original_error=e
            )

    async def get_package_details(self, package_id: str) -> TravelPackage:
        """Get detailed flight information from Aero."""
        try:
            return await self._get_package_details_provider(package_id)
        except Exception as e:
            logger.error(f"Unexpected error getting Aero flight details: {e}")
            raise

    async def _get_package_details_provider(self, package_id: str) -> TravelPackage:
        """Get detailed flight information from Aero provider."""
        try:
            async with self._session.get(f"{self.DETAILS_ENDPOINT}/{package_id}") as response:
                if response.status == 401:
                    await self._authenticate()
                    return await self._get_package_details_provider(package_id)
                elif response.status == 404:
                    raise ValidationError(
                        f"Package not found: {package_id}",
                        "AERO"
                    )
                elif response.status == 429:
                    raise RateLimitError(
                        "Details rate limit exceeded",
                        "AERO"
                    )
                
                response.raise_for_status()
                data = await response.json()
                return self._parse_package(data, include_raw=True)
        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"Failed to get flight details from Aero: {str(e)}",
                "AERO",
                original_error=e
            )

    async def check_availability(self, package_id: str) -> bool:
        """Check flight availability in Aero."""
        try:
            async with self._session.get(f"{self.DETAILS_ENDPOINT}/{package_id}/availability") as response:
                if response.status == 401:
                    await self._authenticate()
                    return await self.check_availability(package_id)
                elif response.status == 404:
                    return False
                elif response.status == 429:
                    raise RateLimitError(
                        "Availability check rate limit exceeded",
                        "AERO"
                    )
                
                response.raise_for_status()
                data = await response.json()
                return data["seats_available"] > 0
        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"Failed to check availability in Aero: {str(e)}",
                "AERO",
                original_error=e
            )

    async def close(self):
        """Close Aero session."""
        if hasattr(self, "_session"):
            await self._session.close()

    def _build_search_params(self, criteria: SearchCriteria) -> Dict:
        """Build search parameters for Aero API."""
        params = {
            "from": criteria.origin,
            "to": criteria.destination,
            "departure": criteria.departure_date,
            "passengers": {
                "adults": criteria.adults,
                "children": criteria.children,
                "infants": criteria.infants
            }
        }
        if criteria.return_date:
            params["return"] = criteria.return_date
        if criteria.class_type:
            params["cabin_class"] = criteria.class_type
        return params

    def _parse_package(self, data: Dict, include_raw: bool = False) -> TravelPackage:
        """Parse Aero API response into TravelPackage model."""
        return TravelPackage(
            id=data["flight_id"],
            provider="AERO",
            origin=data["departure"]["airport"],
            destination=data["arrival"]["airport"],
            departure_date=data["departure"]["datetime"],
            return_date=data.get("return", {}).get("datetime"),
            price=float(data["fare"]["amount"]),
            currency=data["fare"]["currency"],
            availability=data["seats_available"],
            details={
                "airline": data["airline"],
                "flight_number": data["flight_number"],
                "aircraft": data.get("aircraft"),
                "duration": data["duration"],
                "cabin_class": data.get("cabin_class"),
                "baggage_allowance": data.get("baggage"),
                "refundable": data.get("refundable", False),
                "stops": [
                    {
                        "airport": stop["airport"],
                        "duration": stop["duration"]
                    }
                    for stop in data.get("stops", [])
                ]
            },
            raw_data=data if include_raw else None
        )

    async def _get_cached_token(self) -> Optional[Dict]:
        # Implement cache logic here
        pass

    async def _cache_token(self, token_data: Dict) -> None:
        # Implement cache logic here
        pass
