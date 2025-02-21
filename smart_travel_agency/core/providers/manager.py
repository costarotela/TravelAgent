"""
Sistema avanzado de integración con proveedores.

Este módulo implementa:
1. Integración con múltiples proveedores
2. Monitoreo en tiempo real
3. Optimización de consultas
4. Detección de cambios
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

from .scrapers import OlaScraper, AeroScraper, ScraperError
from .scrapers.config import OlaScraperConfig, AeroScraperConfig
from ..schemas import Flight, Accommodation, Activity

# Crear un registro único para las métricas
REGISTRY = CollectorRegistry()

# Métricas
PROVIDER_OPERATIONS = Counter(
    "provider_operations_total",
    "Number of provider operations",
    ["provider_id", "operation_type"],
    registry=REGISTRY
)

PROVIDER_LATENCY = Histogram(
    "provider_operation_latency_seconds",
    "Latency of provider operations",
    ["provider_id", "operation_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
    registry=REGISTRY
)

ACTIVE_MONITORS = Gauge(
    "active_monitors_total", "Number of active package monitors", ["provider_id"],
    registry=REGISTRY
)

PRICE_CHANGES = Histogram(
    "package_price_changes_percentage",
    "Percentage changes in package prices",
    ["provider_id"],
    buckets=[-50, -20, -10, -5, 0, 5, 10, 20, 50],
    registry=REGISTRY
)


@dataclass
class SearchCriteria:
    """Criterios de búsqueda de paquetes."""

    destination: str
    start_date: datetime
    end_date: datetime
    adults: int = 2
    children: int = 0
    max_price: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    categories: Optional[List[str]] = None
    preferred_airlines: Optional[List[str]] = None
    min_rating: Optional[float] = None


@dataclass
class SearchResult:
    """Resultado de búsqueda."""

    provider_id: str
    flights: List[Flight] = field(default_factory=list)
    accommodations: List[Accommodation] = field(default_factory=list)
    activities: List[Activity] = field(default_factory=list)
    error: Optional[str] = None


class ProviderIntegrationManager:
    """Gestor avanzado de integración con proveedores."""

    def __init__(self):
        """Inicializar gestor."""
        self.logger = logging.getLogger(__name__)
        self.initialized = False
        self.scrapers: Dict[str, Union[OlaScraper, AeroScraper]] = {}
        self.scraper_configs: Dict[str, Dict[str, str]] = {}

    async def initialize(self, scraper_configs: Dict[str, Dict[str, str]]) -> None:
        """Inicializar el gestor con configuraciones de scrapers.
        
        Args:
            scraper_configs: Diccionario con configuraciones de scrapers
                           {"ola": {"username": "user", "password": "pass"},
                            "aero": {"username": "user", "password": "pass"}}
        """
        if self.initialized:
            return

        self.logger.info("Inicializando ProviderIntegrationManager")
        self.scraper_configs = scraper_configs

        # Configurar scrapers
        if "ola" in scraper_configs:
            config = OlaScraperConfig(
                requests_per_minute=30,
                extract_cancellation_policy=True,
                extract_baggage_info=True
            )
            self.scrapers["ola"] = OlaScraper(
                username=scraper_configs["ola"]["username"],
                password=scraper_configs["ola"]["password"],
                config=config
            )

        if "aero" in scraper_configs:
            config = AeroScraperConfig(
                requests_per_minute=40,
                extract_cancellation_policy=True,
                extract_baggage_info=True
            )
            self.scrapers["aero"] = AeroScraper(
                username=scraper_configs["aero"]["username"],
                password=scraper_configs["aero"]["password"],
                config=config
            )

        self.initialized = True
        self.logger.info("ProviderIntegrationManager inicializado")

    async def search_all_providers(
        self, criteria: SearchCriteria
    ) -> Dict[str, SearchResult]:
        """Buscar en todos los proveedores disponibles.
        
        Args:
            criteria: Criterios de búsqueda
            
        Returns:
            Diccionario con resultados por proveedor
        """
        if not self.initialized:
            raise RuntimeError("ProviderIntegrationManager no inicializado")

        results: Dict[str, SearchResult] = {}
        tasks = []

        # Crear tareas de búsqueda para cada proveedor
        for provider_id, scraper in self.scrapers.items():
            task = asyncio.create_task(
                self._search_provider(provider_id, scraper, criteria)
            )
            tasks.append((provider_id, task))

        # Esperar resultados
        for provider_id, task in tasks:
            try:
                result = await task
                results[provider_id] = result
            except Exception as e:
                self.logger.error(f"Error buscando en {provider_id}: {e}")
                results[provider_id] = SearchResult(
                    provider_id=provider_id,
                    error=str(e)
                )

        return results

    async def _search_provider(
        self,
        provider_id: str,
        scraper: Union[OlaScraper, AeroScraper],
        criteria: SearchCriteria
    ) -> SearchResult:
        """Buscar en un proveedor específico.
        
        Args:
            provider_id: ID del proveedor
            scraper: Instancia del scraper
            criteria: Criterios de búsqueda
            
        Returns:
            Resultado de búsqueda
        """
        start_time = datetime.now()
        result = SearchResult(provider_id=provider_id)

        try:
            async with scraper:
                # Buscar vuelos
                flights = await scraper.search_flights(
                    origin="EZE",  # TODO: Hacer configurable
                    destination=criteria.destination,
                    departure_date=criteria.start_date,
                    return_date=criteria.end_date,
                    adults=criteria.adults,
                    children=criteria.children
                )
                result.flights = [
                    f for f in flights
                    if (not criteria.preferred_airlines or
                        f.airline in criteria.preferred_airlines)
                ]

                # Buscar alojamiento
                accommodations = await scraper.search_accommodations(
                    destination=criteria.destination,
                    check_in=criteria.start_date,
                    check_out=criteria.end_date,
                    adults=criteria.adults,
                    children=criteria.children
                )
                result.accommodations = [
                    a for a in accommodations
                    if not criteria.min_rating or a.rating >= criteria.min_rating
                ]

                # Buscar actividades
                activities = await scraper.search_activities(
                    destination=criteria.destination,
                    date=criteria.start_date,
                    participants=criteria.adults + criteria.children
                )
                result.activities = activities

        except ScraperError as e:
            self.logger.error(f"Error en scraper {provider_id}: {e}")
            result.error = str(e)

        finally:
            # Registrar métricas
            duration = (datetime.now() - start_time).total_seconds()
            PROVIDER_OPERATIONS.labels(
                provider_id=provider_id,
                operation_type="search"
            ).inc()
            PROVIDER_LATENCY.labels(
                provider_id=provider_id,
                operation_type="search"
            ).observe(duration)

        return result


# Instancia global
provider_manager = ProviderIntegrationManager()


def get_provider_manager() -> ProviderIntegrationManager:
    """Obtener instancia única del gestor."""
    return provider_manager
