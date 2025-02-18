"""OLA Travel provider implementation."""

import logging
from typing import Dict, List, Optional
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup

from .base import BaseProvider, SearchCriteria, TravelPackage
from .ola_dynamic_updater import OLAUpdater, OLAMonitor
from .ola_models import PaqueteOLA

logger = logging.getLogger(__name__)


class OlaProvider(BaseProvider):
    """Provider implementation for OLA Travel with dynamic update."""

    def __init__(self, config: Dict):
        """Initialize OLA provider."""
        super().__init__(config)
        self.monitor = OLAMonitor()
        self.updater = OLAUpdater(config, monitor=self.monitor)
        self.update_interval = config.get("update_interval", 3600)  # 1 hour by default

    async def search(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """Search for travel packages in OLA with dynamic update."""
        try:
            # Update data if necessary
            await self.updater.fetch_data(criteria.destination)

            # Perform search in cache
            results = self._search_cached_packages(criteria)

            return results
        except Exception as e:
            self.monitor.log_error()
            raise

    def _search_cached_packages(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """Search in local cache using provided criteria."""
        cached_data = self.updater.cache
        results = []

        for package_hash, package in cached_data.items():
            if self._matches_criteria(package, criteria):
                results.append(self._parse_package(package))

        return results

    def _matches_criteria(self, package: PaqueteOLA, criteria: SearchCriteria) -> bool:
        """Check if a package matches search criteria."""
        if criteria.destination and package.destino != criteria.destination:
            return False

        if criteria.max_price and package.precio > criteria.max_price:
            return False

        if criteria.start_date:
            start_date = datetime.strptime(criteria.start_date, "%Y-%m-%d")
            if not any(fecha >= start_date for fecha in package.fechas):
                return False

        if criteria.end_date:
            end_date = datetime.strptime(criteria.end_date, "%Y-%m-%d")
            if not any(fecha <= end_date for fecha in package.fechas):
                return False

        return True

    def _parse_package(self, data: PaqueteOLA) -> TravelPackage:
        """Parse OLA API response into TravelPackage model."""
        package = TravelPackage(
            id=data.data_hash,
            provider="OLA",
            origin=data.origen,
            destination=data.destino,
            departure_date=data.fechas[0],
            return_date=data.fechas[-1],
            price=float(data.precio),
            currency=data.moneda,
            availability=data.disponibilidad,
            details={
                "airline": data.aerolinea,
                "flight_number": data.numero_vuelo,
                "duration": data.duracion,
                "stops": data.escalas,
                "amenities": data.servicios,
                "cancellation_policy": data.politica_cancelacion,
            },
            raw_data=data,
        )
        return package

    async def get_package_details(self, package_id: str) -> Optional[TravelPackage]:
        """Get detailed package information from OLA."""
        try:
            # Search in cache first
            for package in self.updater.cache.values():
                if package.data_hash == package_id:
                    return self._parse_package(package)

            return None
        except Exception as e:
            self.monitor.log_error()
            raise

    async def check_availability(self, package_id: str) -> bool:
        """Check package availability in OLA."""
        try:
            # Search in cache first
            for package in self.updater.cache.values():
                if package.data_hash == package_id:
                    return package.disponibilidad

            return False
        except Exception as e:
            self.monitor.log_error()
            raise

    async def close(self):
        """Close OLA session."""
        if hasattr(self, "_session"):
            await self._session.close()
