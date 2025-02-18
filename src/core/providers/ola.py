"""OLA Travel provider implementation."""

import logging
from typing import Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

from .base import BaseProvider, SearchCriteria, TravelPackage

logger = logging.getLogger(__name__)


class OlaProvider(BaseProvider):
    """Provider implementation for OLA Travel."""

    BASE_URL = "https://api.ola.com/v2"
    SEARCH_ENDPOINT = "/search"
    DETAILS_ENDPOINT = "/packages"

    def _validate_credentials(self) -> None:
        """Validate OLA credentials."""
        required_fields = ["api_key", "api_secret"]
        for field in required_fields:
            if field not in self.credentials:
                raise ValueError(f"Missing required credential: {field}")

    def _setup_session(self) -> None:
        """Setup OLA session with proper headers and configuration."""
        self._session = aiohttp.ClientSession(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.credentials['api_key']}",
                "X-API-Secret": self.credentials["api_secret"],
                "Content-Type": "application/json",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        )

    async def search(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """Search for travel packages in OLA."""
        try:
            search_params = self._build_search_params(criteria)
            async with self._session.get(
                self.SEARCH_ENDPOINT, params=search_params
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return [self._parse_package(pkg) for pkg in data["packages"]]
        except aiohttp.ClientError as e:
            logger.error(f"Error searching OLA packages: {e}")
            raise ConnectionError(f"Failed to connect to OLA: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during OLA search: {e}")
            raise

    async def get_package_details(self, package_id: str) -> TravelPackage:
        """Get detailed package information from OLA."""
        try:
            async with self._session.get(
                f"{self.DETAILS_ENDPOINT}/{package_id}"
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return self._parse_package(data, include_raw=True)
        except aiohttp.ClientError as e:
            logger.error(f"Error getting OLA package details: {e}")
            raise ConnectionError(f"Failed to get package details from OLA: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting OLA package details: {e}")
            raise

    async def check_availability(self, package_id: str) -> bool:
        """Check package availability in OLA."""
        try:
            async with self._session.get(
                f"{self.DETAILS_ENDPOINT}/{package_id}/availability"
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data["available"]
        except aiohttp.ClientError as e:
            logger.error(f"Error checking OLA package availability: {e}")
            raise ConnectionError(f"Failed to check availability in OLA: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking OLA availability: {e}")
            raise

    async def close(self):
        """Close OLA session."""
        if hasattr(self, "_session"):
            await self._session.close()

    def _build_search_params(self, criteria: SearchCriteria) -> Dict:
        """Build search parameters for OLA API."""
        params = {
            "origin": criteria.origin,
            "destination": criteria.destination,
            "departure_date": criteria.departure_date,
            "adults": criteria.adults,
            "children": criteria.children,
            "infants": criteria.infants,
        }
        if criteria.return_date:
            params["return_date"] = criteria.return_date
        if criteria.class_type:
            params["class"] = criteria.class_type
        return params

    def _parse_package(self, data: Dict, include_raw: bool = False) -> TravelPackage:
        """Parse OLA API response into TravelPackage model."""
        package = TravelPackage(
            id=data["id"],
            provider="OLA",
            origin=data["origin"],
            destination=data["destination"],
            departure_date=data["departure_date"],
            return_date=data.get("return_date"),
            price=float(data["price"]["amount"]),
            currency=data["price"]["currency"],
            availability=data["availability"],
            details={
                "airline": data.get("airline"),
                "flight_number": data.get("flight_number"),
                "duration": data.get("duration"),
                "stops": data.get("stops", []),
                "amenities": data.get("amenities", []),
                "cancellation_policy": data.get("cancellation_policy"),
            },
            raw_data=data if include_raw else None,
        )
        return package
