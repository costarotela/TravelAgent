"""
Sistema avanzado de integración con proveedores.

Este módulo implementa:
1. Integración con múltiples proveedores
2. Monitoreo en tiempo real
3. Optimización de consultas
4. Detección de cambios
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import asyncio
from decimal import Decimal
import aiohttp
from dataclasses import dataclass
from prometheus_client import Counter, Histogram, Gauge

# Métricas
PROVIDER_OPERATIONS = Counter(
    "provider_operations_total",
    "Number of provider operations",
    ["provider_id", "operation_type"],
)

PROVIDER_LATENCY = Histogram(
    "provider_operation_latency_seconds",
    "Latency of provider operations",
    ["provider_id", "operation_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
)

ACTIVE_MONITORS = Gauge(
    "active_monitors_total", "Number of active package monitors", ["provider_id"]
)

PRICE_CHANGES = Histogram(
    "package_price_changes_percentage",
    "Percentage changes in package prices",
    ["provider_id"],
    buckets=[-50, -20, -10, -5, 0, 5, 10, 20, 50],
)


@dataclass
class SearchCriteria:
    """Criterios de búsqueda de paquetes."""

    destination: str
    start_date: datetime
    end_date: datetime
    adults: int
    children: Optional[int] = 0
    max_price: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    categories: Optional[List[str]] = None


@dataclass
class TravelPackage:
    """Paquete de viaje con datos de optimización."""

    id: str
    provider_id: str
    name: str
    destination: str
    price: Decimal
    original_price: Optional[Decimal] = None
    discount_percentage: Optional[float] = None
    availability: Dict[str, Any] = None
    optimization_history: List[Dict[str, Any]] = None
    last_update: datetime = None
    status: str = "active"


class ProviderIntegrationManager:
    """
    Gestor avanzado de integración con proveedores.
    """

    def __init__(self, update_interval: int = 300):
        """
        Inicializar gestor.

        Args:
            update_interval: Intervalo de actualización en segundos
        """
        self.update_interval = update_interval
        self.providers: Dict[str, Any] = {}
        self._active_monitors: Dict[str, asyncio.Task] = {}
        self._last_update: Dict[str, datetime] = {}
        self.logger = logging.getLogger(__name__)
        self.initialized = False

        # Configuración de optimización
        self.min_price_change = Decimal("0.5")  # 0.5% mínimo para registrar cambio
        self.optimization_window = timedelta(hours=24)  # Ventana de análisis

        # Iniciar tarea de limpieza
        asyncio.create_task(self._cleanup_task())

    async def initialize(self) -> None:
        """Inicializar el gestor."""
        if self.initialized:
            return

        self.logger.info("Inicializando ProviderIntegrationManager")

        # Cargar proveedores registrados
        # TODO: Implementar carga desde configuración

        self.initialized = True
        self.logger.info("ProviderIntegrationManager inicializado")

    async def register_provider(self, provider_id: str, provider: Any) -> None:
        """
        Registrar nuevo proveedor.

        Args:
            provider_id: ID del proveedor
            provider: Instancia del proveedor
        """
        self.providers[provider_id] = provider
        self._last_update[provider_id] = datetime.now()

        PROVIDER_OPERATIONS.labels(
            provider_id=provider_id, operation_type="register"
        ).inc()

        self.logger.info(f"Proveedor {provider_id} registrado")

    async def start_monitoring(self, package_ids: List[str], provider_id: str) -> None:
        """
        Iniciar monitoreo de paquetes.

        Args:
            package_ids: Lista de IDs de paquetes
            provider_id: ID del proveedor
        """
        if provider_id not in self.providers:
            raise ValueError(f"Proveedor {provider_id} no registrado")

        for package_id in package_ids:
            monitor_key = f"{provider_id}:{package_id}"

            if monitor_key in self._active_monitors:
                continue

            self._active_monitors[monitor_key] = asyncio.create_task(
                self._monitor_package(package_id, provider_id)
            )

            ACTIVE_MONITORS.labels(provider_id=provider_id).inc()

    async def stop_monitoring(self, package_ids: List[str], provider_id: str) -> None:
        """
        Detener monitoreo de paquetes.

        Args:
            package_ids: Lista de IDs de paquetes
            provider_id: ID del proveedor
        """
        for package_id in package_ids:
            monitor_key = f"{provider_id}:{package_id}"

            if monitor_key in self._active_monitors:
                self._active_monitors[monitor_key].cancel()
                del self._active_monitors[monitor_key]
                ACTIVE_MONITORS.labels(provider_id=provider_id).dec()

    async def get_package_data(
        self, package_id: str, provider_id: str, force_refresh: bool = False
    ) -> Optional[TravelPackage]:
        """
        Obtener datos actualizados de paquete.

        Args:
            package_id: ID del paquete
            provider_id: ID del proveedor
            force_refresh: Forzar actualización

        Returns:
            Datos del paquete o None
        """
        start_time = datetime.now()
        try:
            provider = self.providers.get(provider_id)
            if not provider:
                raise ValueError(f"Proveedor {provider_id} no registrado")

            package_data = await provider.get_package_details(package_id)

            if package_data:
                # Registrar métricas
                PROVIDER_OPERATIONS.labels(
                    provider_id=provider_id, operation_type="get_package"
                ).inc()

                return TravelPackage(**package_data)

            return None

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            PROVIDER_LATENCY.labels(
                provider_id=provider_id, operation_type="get_package"
            ).observe(duration)

    async def search_packages(
        self,
        criteria: SearchCriteria,
        provider_ids: Optional[List[str]] = None,
        optimization_enabled: bool = True,
    ) -> List[Tuple[str, TravelPackage]]:
        """
        Buscar paquetes con optimización.

        Args:
            criteria: Criterios de búsqueda
            provider_ids: Lista de proveedores
            optimization_enabled: Habilitar optimización

        Returns:
            Lista de tuplas (provider_id, package)
        """
        if not provider_ids:
            provider_ids = list(self.providers.keys())

        search_tasks = []
        for provider_id in provider_ids:
            if provider_id in self.providers:
                search_tasks.append(
                    self._search_provider(provider_id, criteria, optimization_enabled)
                )

        results = await asyncio.gather(*search_tasks, return_exceptions=True)

        packages = []
        for provider_id, result in zip(provider_ids, results):
            if isinstance(result, Exception):
                self.logger.error(
                    f"Error searching provider {provider_id}: {str(result)}"
                )
                continue

            packages.extend((provider_id, pkg) for pkg in result)

        return packages

    async def _monitor_package(self, package_id: str, provider_id: str) -> None:
        """Monitorear cambios en paquete."""
        while True:
            try:
                previous_data = await self.get_package_data(package_id, provider_id)

                await asyncio.sleep(self.update_interval)

                current_data = await self.get_package_data(
                    package_id, provider_id, force_refresh=True
                )

                if not current_data or not previous_data:
                    continue

                # Detectar y registrar cambios
                changes = self._detect_changes(previous_data, current_data)

                if changes:
                    if "price" in changes:
                        PRICE_CHANGES.labels(provider_id=provider_id).observe(
                            changes["price"]["percentage"]
                        )

                    # Registrar para optimización
                    await self._register_optimization_data(
                        package_id, provider_id, changes
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring package {package_id}: {str(e)}")
                await asyncio.sleep(self.update_interval)

    async def _search_provider(
        self,
        provider_id: str,
        criteria: SearchCriteria,
        optimization_enabled: bool = True,
    ) -> List[TravelPackage]:
        """
        Realizar búsqueda en proveedor con optimización.

        Args:
            provider_id: ID del proveedor
            criteria: Criterios de búsqueda
            optimization_enabled: Habilitar optimización
        """
        start_time = datetime.now()
        try:
            provider = self.providers[provider_id]
            results = await provider.search_packages(criteria)

            if results and optimization_enabled:
                # Aplicar optimizaciones basadas en histórico
                results = await self._optimize_results(provider_id, results)

            PROVIDER_OPERATIONS.labels(
                provider_id=provider_id, operation_type="search"
            ).inc()

            return results

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            PROVIDER_LATENCY.labels(
                provider_id=provider_id, operation_type="search"
            ).observe(duration)

    def _detect_changes(
        self, previous: TravelPackage, current: TravelPackage
    ) -> Dict[str, Any]:
        """
        Detectar cambios significativos.

        Args:
            previous: Versión anterior del paquete
            current: Versión actual del paquete

        Returns:
            Diccionario con cambios detectados
        """
        changes = {}

        # Cambios en precio
        if (
            abs((current.price - previous.price) / previous.price)
            > self.min_price_change
        ):
            changes["price"] = {
                "previous": float(previous.price),
                "current": float(current.price),
                "difference": float(current.price - previous.price),
                "percentage": float(
                    ((current.price - previous.price) / previous.price) * 100
                ),
            }

        # Cambios en disponibilidad
        if previous.availability != current.availability:
            changes["availability"] = {
                "previous": previous.availability,
                "current": current.availability,
            }

        # Cambios en estado
        if previous.status != current.status:
            changes["status"] = {"previous": previous.status, "current": current.status}

        return changes

    async def _register_optimization_data(
        self, package_id: str, provider_id: str, changes: Dict[str, Any]
    ) -> None:
        """
        Registrar datos para optimización.

        Args:
            package_id: ID del paquete
            provider_id: ID del proveedor
            changes: Cambios detectados
        """
        # TODO: Implementar registro en base de datos
        pass

    async def _optimize_results(
        self, provider_id: str, packages: List[TravelPackage]
    ) -> List[TravelPackage]:
        """
        Optimizar resultados basado en histórico.

        Args:
            provider_id: ID del proveedor
            packages: Lista de paquetes

        Returns:
            Lista de paquetes optimizada
        """
        # TODO: Implementar optimización basada en histórico
        return packages

    async def _cleanup_task(self):
        """Tarea periódica de limpieza."""
        while True:
            try:
                # Limpiar monitores inactivos
                current_time = datetime.now()
                for key, task in list(self._active_monitors.items()):
                    if task.done():
                        provider_id = key.split(":")[0]
                        del self._active_monitors[key]
                        ACTIVE_MONITORS.labels(provider_id=provider_id).dec()

                await asyncio.sleep(300)  # 5 minutos

            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)


# Instancia global
provider_manager = ProviderIntegrationManager()


async def get_provider_manager() -> ProviderIntegrationManager:
    """Obtener instancia única del gestor."""
    return provider_manager
