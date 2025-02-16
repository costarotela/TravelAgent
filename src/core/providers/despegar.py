"""Despegar provider implementation."""
import logging
from typing import Dict, List, Optional
from urllib.parse import urlencode

import aiohttp
from bs4 import BeautifulSoup

from .base import BaseProvider, SearchCriteria, TravelPackage

logger = logging.getLogger(__name__)


class DespegarProvider(BaseProvider):
    """Provider implementation for Despegar."""

    BASE_URL = "https://api.despegar.com/v3"
    SEARCH_ENDPOINT = "/flights/search"
    DETAILS_ENDPOINT = "/flights"
    AVAILABILITY_ENDPOINT = "/availability"

    def _validate_credentials(self) -> None:
        """Validate Despegar credentials."""
        required_fields = ["api_key", "affiliate_id"]
        for field in required_fields:
            if field not in self.credentials:
                raise ValueError(f"Missing required credential: {field}")

    def _setup_session(self) -> None:
        """Setup Despegar session with API key authentication."""
        self._session = aiohttp.ClientSession(
            base_url=self.BASE_URL,
            headers={
                "X-API-Key": self.credentials["api_key"],
                "X-Affiliate-ID": self.credentials["affiliate_id"],
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def search(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """Search for travel packages in Despegar."""
        try:
            search_params = self._build_search_params(criteria)
            async with self._session.get(
                self.SEARCH_ENDPOINT,
                params=search_params,
                headers=self._get_tracking_headers()
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return [self._parse_package(item) for item in data["items"]]
        except aiohttp.ClientError as e:
            logger.error(f"Error searching Despegar packages: {e}")
            raise ConnectionError(f"Failed to search Despegar packages: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during Despegar search: {e}")
            raise

    async def get_package_details(self, package_id: str) -> TravelPackage:
        """Get detailed package information from Despegar."""
        try:
            async with self._session.get(
                f"{self.DETAILS_ENDPOINT}/{package_id}",
                headers=self._get_tracking_headers()
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return self._parse_package(data, include_raw=True)
        except aiohttp.ClientError as e:
            logger.error(f"Error getting Despegar package details: {e}")
            raise ConnectionError(f"Failed to get package details from Despegar: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting Despegar package details: {e}")
            raise

    async def check_availability(self, package_id: str) -> bool:
        """Check package availability in Despegar."""
        try:
            async with self._session.get(
                f"{self.DETAILS_ENDPOINT}/{package_id}{self.AVAILABILITY_ENDPOINT}",
                headers=self._get_tracking_headers()
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data["status"] == "AVAILABLE"
        except aiohttp.ClientError as e:
            logger.error(f"Error checking Despegar package availability: {e}")
            raise ConnectionError(f"Failed to check availability in Despegar: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking Despegar availability: {e}")
            raise

    async def close(self):
        """Close Despegar session."""
        if hasattr(self, "_session"):
            await self._session.close()

    def _build_search_params(self, criteria: SearchCriteria) -> Dict:
        """Build search parameters for Despegar API."""
        params = {
            "from": criteria.origin,
            "to": criteria.destination,
            "departure": criteria.departure_date,
            "adults": criteria.adults,
            "children": criteria.children,
            "infants": criteria.infants,
        }
        if criteria.return_date:
            params["return"] = criteria.return_date
        if criteria.class_type:
            params["cabin"] = criteria.class_type
        return params

    def _get_tracking_headers(self) -> Dict[str, str]:
        """Get tracking headers for Despegar API."""
        return {
            "X-Flow-Id": "search",
            "X-Track-ID": "travel-agent",
            "X-Device-Type": "API"
        }

    def _parse_package(self, data: Dict, include_raw: bool = False) -> TravelPackage:
        """Parse Despegar API response into TravelPackage model."""
        flight_info = data["flight"]
        price_info = data["price"]
        
        return TravelPackage(
            id=data["id"],
            provider="DESPEGAR",
            origin=flight_info["departure"]["airport"]["code"],
            destination=flight_info["arrival"]["airport"]["code"],
            departure_date=flight_info["departure"]["date"],
            return_date=flight_info.get("return", {}).get("date"),
            price=float(price_info["amount"]),
            currency=price_info["currency"],
            availability=data["availability"]["seats"],
            details={
                "airline": flight_info["airline"]["name"],
                "flight_number": flight_info["number"],
                "duration": flight_info["duration"],
                "cabin_class": flight_info.get("cabin", {}).get("type"),
                "baggage": data.get("baggage", {}),
                "cancellation_policy": data.get("policies", {}).get("cancellation"),
                "stops": [
                    {
                        "airport": stop["airport"]["code"],
                        "duration": stop["duration"]
                    }
                    for stop in flight_info.get("stops", [])
                ],
                "amenities": data.get("amenities", [])
            },
            raw_data=data if include_raw else None
        )
