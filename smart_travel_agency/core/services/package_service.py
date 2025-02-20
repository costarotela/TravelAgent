"""
Servicio para gestionar paquetes de viaje.

Este módulo implementa la lógica de negocio para:
1. Calcular precios totales
2. Validar paquetes
3. Gestionar fechas
4. Optimizar precios
5. Integración con proveedores
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

from ..schemas import TravelPackage, Flight, Accommodation, Activity
from ..providers.manager import ProviderIntegrationManager, SearchCriteria, SearchResult
from ..analysis.price_optimizer.optimizer import PriceOptimizer, OptimizationResult


@dataclass
class PackageSearchResult:
    """Resultado de búsqueda de paquetes."""
    
    packages: List[TravelPackage]
    optimization_results: List[OptimizationResult]
    provider_results: Dict[str, SearchResult]
    errors: List[str] = None


class PackageService:
    """Servicio para gestionar paquetes de viaje."""

    _instance = None

    def __new__(cls):
        """Implementa el patrón Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Inicializa las dependencias del servicio."""
        self.provider_manager = ProviderIntegrationManager()
        self.price_optimizer = PriceOptimizer()
        self.logger = logging.getLogger(__name__)

    @classmethod
    def get_instance(cls) -> "PackageService":
        """Obtiene la instancia única del servicio."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def initialize_providers(self, scraper_configs: Dict[str, Dict[str, str]]) -> None:
        """Inicializa los proveedores con sus configuraciones.
        
        Args:
            scraper_configs: Configuraciones de los scrapers
        """
        await self.provider_manager.initialize(scraper_configs)

    async def search_and_optimize_packages(
        self,
        destination: str,
        start_date: datetime,
        end_date: datetime,
        adults: int = 2,
        children: int = 0,
        **kwargs
    ) -> PackageSearchResult:
        """Busca y optimiza paquetes de viaje.
        
        Args:
            destination: Destino del viaje
            start_date: Fecha de inicio
            end_date: Fecha de fin
            adults: Número de adultos
            children: Número de niños
            **kwargs: Criterios adicionales de búsqueda
            
        Returns:
            Resultado de la búsqueda y optimización
        """
        try:
            # Crear criterios de búsqueda
            criteria = SearchCriteria(
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                adults=adults,
                children=children,
                **kwargs
            )

            # Buscar en proveedores
            provider_results = await self.provider_manager.search_all_providers(criteria)

            # Convertir resultados en paquetes
            packages = []
            errors = []

            for provider_id, result in provider_results.items():
                if result.error:
                    errors.append(f"Error en {provider_id}: {result.error}")
                    continue

                # Crear paquetes combinando vuelos, alojamiento y actividades
                packages.extend(
                    await self._create_packages_from_results(result, provider_id)
                )

            # Optimizar precios
            optimization_results = await self.price_optimizer.optimize_prices_batch(packages)

            # Actualizar precios en paquetes
            for package, opt_result in zip(packages, optimization_results):
                package.total_price = opt_result.optimal_price
                package.margin = opt_result.margin

            return PackageSearchResult(
                packages=packages,
                optimization_results=optimization_results,
                provider_results=provider_results,
                errors=errors
            )

        except Exception as e:
            self.logger.error(f"Error en búsqueda de paquetes: {str(e)}")
            raise

    async def _create_packages_from_results(
        self,
        result: SearchResult,
        provider_id: str
    ) -> List[TravelPackage]:
        """Crea paquetes a partir de los resultados de búsqueda.
        
        Args:
            result: Resultado de búsqueda
            provider_id: ID del proveedor
            
        Returns:
            Lista de paquetes
        """
        packages = []

        # Crear todas las combinaciones posibles de vuelos y alojamiento
        for flight in result.flights:
            for accommodation in result.accommodations:
                # Verificar que las fechas coincidan
                if (accommodation.check_in <= flight.arrival_time and
                    accommodation.check_out >= flight.departure_time):
                    
                    # Crear paquete base
                    package = TravelPackage(
                        provider_id=provider_id,
                        flights=[flight],
                        accommodation=accommodation,
                        activities=[],  # Se agregarán después
                        start_date=flight.departure_time,
                        end_date=flight.arrival_time
                    )

                    # Agregar actividades que coincidan con las fechas
                    package.activities = [
                        activity for activity in result.activities
                        if (activity.date >= package.start_date and
                            activity.date <= package.end_date)
                    ]

                    # Validar y agregar paquete
                    if self.validate_package(package):
                        package.total_price = self.calculate_total_price(package)
                        packages.append(package)

        return packages

    @classmethod
    def calculate_total_price(cls, package: TravelPackage) -> Decimal:
        """Calcula el precio total del paquete.

        Args:
            package: Paquete a calcular

        Returns:
            Precio total del paquete
        """
        if not package:
            return Decimal("0")

        total = Decimal("0")

        # Sumar vuelos
        for flight in package.flights:
            total += flight.price

        # Sumar alojamiento
        if package.accommodation:
            total += package.accommodation.total_price

        # Sumar actividades
        for activity in package.activities:
            if activity.included:
                total += activity.price

        # Aplicar margen
        total *= (Decimal("1.0") + package.margin)

        return total

    def calculate_check_in_date(self, package: TravelPackage) -> datetime:
        """Calcula la fecha de check-in.

        Args:
            package: Paquete a calcular

        Returns:
            Fecha de check-in
        """
        if not package or not package.flights:
            return package.start_date

        # Usar la fecha de llegada del primer vuelo
        arrival_flight = min(package.flights, key=lambda f: f.arrival_time)
        return arrival_flight.arrival_time

    def calculate_check_out_date(self, package: TravelPackage) -> datetime:
        """Calcula la fecha de check-out.

        Args:
            package: Paquete a calcular

        Returns:
            Fecha de check-out
        """
        if not package or not package.flights:
            return package.end_date

        # Usar la fecha de salida del último vuelo
        departure_flight = max(package.flights, key=lambda f: f.departure_time)
        return departure_flight.departure_time

    def calculate_nights(self, package: TravelPackage) -> int:
        """Calcula el número de noches.

        Args:
            package: Paquete a calcular

        Returns:
            Número de noches
        """
        if not package:
            return 0

        check_in = self.calculate_check_in_date(package)
        check_out = self.calculate_check_out_date(package)

        # Calcular diferencia en días
        delta = check_out - check_in
        return delta.days

    def validate_package(self, package: TravelPackage) -> bool:
        """Valida que el paquete sea válido.

        Args:
            package: Paquete a validar

        Returns:
            True si el paquete es válido
        """
        if not package:
            return False

        try:
            # Validar fechas
            if package.end_date <= package.start_date:
                return False

            # Validar vuelos
            if not package.flights:
                return False

            # Validar que los vuelos estén en orden
            for i in range(len(package.flights) - 1):
                if package.flights[i].arrival_time >= package.flights[i + 1].departure_time:
                    return False

            # Validar alojamiento
            if package.accommodation:
                check_in = self.calculate_check_in_date(package)
                check_out = self.calculate_check_out_date(package)

                if package.accommodation.check_in > check_in or \
                   package.accommodation.check_out < check_out:
                    return False

            # Validar actividades
            for activity in package.activities:
                if activity.date < package.start_date or \
                   activity.date > package.end_date:
                    return False

            return True

        except Exception:
            return False
