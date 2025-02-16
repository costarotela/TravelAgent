"""Aero provider implementation."""
import logging
from typing import Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from .base import BaseProvider, SearchCriteria, TravelPackage

logger = logging.getLogger(__name__)


class AeroProvider(BaseProvider):
    """Provider implementation for Aero."""

    BASE_URL = "https://api.aero.com"
    AUTH_ENDPOINT = "/auth/token"
    SEARCH_ENDPOINT = "/flights/search"
    DETAILS_ENDPOINT = "/flights/details"

    def _validate_credentials(self) -> None:
        """Validate Aero credentials."""
        required_fields = ["client_id", "client_secret"]
        for field in required_fields:
            if field not in self.credentials:
                raise ValueError(f"Missing required credential: {field}")

    async def _setup_session(self) -> None:
        """Setup Aero session with OAuth authentication."""
        self._session = aiohttp.ClientSession(
            base_url=self.BASE_URL,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        await self._authenticate()

    async def _authenticate(self) -> None:
        """Authenticate with Aero API using OAuth."""
        try:
            auth_data = {
                "grant_type": "client_credentials",
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"]
            }
            async with self._session.post(self.AUTH_ENDPOINT, json=auth_data) as response:
                response.raise_for_status()
                token_data = await response.json()
                self._session.headers.update({
                    "Authorization": f"Bearer {token_data['access_token']}",
                    "Content-Type": "application/json"
                })
        except aiohttp.ClientError as e:
            logger.error(f"Authentication failed with Aero: {e}")
            raise ConnectionError(f"Failed to authenticate with Aero: {e}")

    async def search(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """Search for flights in Aero."""
        try:
            search_params = self._build_search_params(criteria)
            async with self._session.post(self.SEARCH_ENDPOINT, json=search_params) as response:
                response.raise_for_status()
                data = await response.json()
                return [self._parse_package(pkg) for pkg in data["flights"]]
        except aiohttp.ClientError as e:
            logger.error(f"Error searching Aero flights: {e}")
            if e.status == 401:
                await self._authenticate()
                return await self.search(criteria)
            raise ConnectionError(f"Failed to search Aero flights: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during Aero search: {e}")
            raise

    async def get_package_details(self, package_id: str) -> TravelPackage:
        """Get detailed flight information from Aero."""
        try:
            async with self._session.get(f"{self.DETAILS_ENDPOINT}/{package_id}") as response:
                response.raise_for_status()
                data = await response.json()
                return self._parse_package(data, include_raw=True)
        except aiohttp.ClientError as e:
            logger.error(f"Error getting Aero flight details: {e}")
            if e.status == 401:
                await self._authenticate()
                return await self.get_package_details(package_id)
            raise ConnectionError(f"Failed to get flight details from Aero: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting Aero flight details: {e}")
            raise

    async def check_availability(self, package_id: str) -> bool:
        """Check flight availability in Aero."""
        try:
            async with self._session.get(f"{self.DETAILS_ENDPOINT}/{package_id}/availability") as response:
                response.raise_for_status()
                data = await response.json()
                return data["seats_available"] > 0
        except aiohttp.ClientError as e:
            logger.error(f"Error checking Aero flight availability: {e}")
            if e.status == 401:
                await self._authenticate()
                return await self.check_availability(package_id)
            raise ConnectionError(f"Failed to check availability in Aero: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking Aero availability: {e}")
            raise

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
