"""
Gestor de integración con proveedores.
Maneja la obtención y actualización de datos en tiempo real.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import asyncio
from decimal import Decimal
import aiohttp
from ..schemas import TravelPackage, SearchCriteria
from ..interfaces import (
    DataProvider,
    StorageManager,
    CacheManager,
    EventEmitter,
    MetricsCollector,
    Logger,
    AgentComponent,
)


class ProviderIntegrationManager(AgentComponent):
    """
    Gestor de integración que maneja:
    1. Conexión con múltiples proveedores
    2. Actualización en tiempo real de datos
    3. Caché y optimización de consultas
    4. Monitoreo de cambios de precios
    """

    def __init__(
        self,
        storage: StorageManager,
        cache: CacheManager,
        logger: Logger,
        metrics: MetricsCollector,
        events: EventEmitter,
        update_interval: int = 300,  # 5 minutos por defecto
    ):
        super().__init__(logger, metrics, events)
        self.storage = storage
        self.cache = cache
        self.update_interval = update_interval
        self.providers: Dict[str, DataProvider] = {}
        self._active_monitors: Dict[str, asyncio.Task] = {}
        self._last_update: Dict[str, datetime] = {}
        self.initialized = False

    async def initialize(self) -> None:
        """Inicializar el componente."""
        if self.initialized:
            return

        self.logger.info("Inicializando ProviderIntegrationManager")

        # Inicializar colecciones
        await self.storage.init_collection("providers")
        await self.storage.init_collection("packages")
        await self.storage.init_collection("price_history")

        # Cargar proveedores registrados
        providers_data = await self.storage.find("providers", {"status": "active"})
        for provider_data in providers_data:
            provider_id = provider_data["id"]
            if provider_id not in self.providers:
                # Aquí podrías tener lógica para recrear el proveedor
                # Por ahora solo lo registramos en el log
                self.logger.info(
                    f"Proveedor {provider_id} encontrado pero no inicializado"
                )

        # Iniciar monitoreo de precios para proveedores activos
        for provider_id in self.providers:
            if provider_id not in self._active_monitors:
                self._active_monitors[provider_id] = asyncio.create_task(
                    self._monitor_price_changes(provider_id)
                )

        self.initialized = True
        self.logger.info("ProviderIntegrationManager inicializado")

    async def shutdown(self) -> None:
        """Cerrar el componente."""
        if not self.initialized:
            return

        self.logger.info("Cerrando ProviderIntegrationManager")

        # Detener todas las tareas de monitoreo
        for task in self._active_monitors.values():
            task.cancel()

        # Esperar a que todas las tareas terminen
        if self._active_monitors:
            await asyncio.gather(
                *self._active_monitors.values(), return_exceptions=True
            )

        # Limpiar estado
        self._active_monitors.clear()
        self._last_update.clear()

        # Desconectar proveedores
        for provider in self.providers.values():
            # Aquí podrías tener lógica para cerrar conexiones de proveedores
            pass

        self.initialized = False
        self.logger.info("ProviderIntegrationManager cerrado")

    async def register_provider(self, provider_id: str, provider: DataProvider) -> None:
        """
        Registrar nuevo proveedor de datos.
        """
        self.providers[provider_id] = provider
        self._last_update[provider_id] = datetime.now()

        self.emit_event(
            "provider_registered",
            {"provider_id": provider_id, "timestamp": datetime.now().isoformat()},
        )

    async def start_monitoring(self, package_ids: List[str], provider_id: str) -> None:
        """
        Iniciar monitoreo de paquetes específicos.
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

    async def stop_monitoring(self, package_ids: List[str], provider_id: str) -> None:
        """
        Detener monitoreo de paquetes específicos.
        """
        for package_id in package_ids:
            monitor_key = f"{provider_id}:{package_id}"

            if monitor_key in self._active_monitors:
                self._active_monitors[monitor_key].cancel()
                del self._active_monitors[monitor_key]

    async def get_package_data(
        self, package_id: str, provider_id: str, force_refresh: bool = False
    ) -> Optional[TravelPackage]:
        """
        Obtener datos actualizados de un paquete.
        """
        cache_key = f"package:{provider_id}:{package_id}"

        if not force_refresh:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return TravelPackage(**cached_data)

        provider = self.providers.get(provider_id)
        if not provider:
            raise ValueError(f"Proveedor {provider_id} no registrado")

        package_data = await provider.get_package_details(package_id)

        if package_data:
            self.cache.set(cache_key, package_data.dict(), ttl=self.update_interval)
            return package_data

        return None

    async def search_packages(
        self, criteria: SearchCriteria, provider_ids: Optional[List[str]] = None
    ) -> List[Tuple[str, TravelPackage]]:
        """
        Buscar paquetes en múltiples proveedores.
        """
        if not provider_ids:
            provider_ids = list(self.providers.keys())

        search_tasks = []
        for provider_id in provider_ids:
            if provider_id in self.providers:
                search_tasks.append(self._search_provider(provider_id, criteria))

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
        """
        Monitorear cambios en un paquete específico.
        """
        while True:
            try:
                previous_data = await self.get_package_data(package_id, provider_id)

                await asyncio.sleep(self.update_interval)

                current_data = await self.get_package_data(
                    package_id, provider_id, force_refresh=True
                )

                if not current_data:
                    continue

                if not previous_data:
                    continue

                # Detectar cambios significativos
                changes = self._detect_changes(previous_data, current_data)

                if changes:
                    self.emit_event(
                        "package_updated",
                        {
                            "package_id": package_id,
                            "provider_id": provider_id,
                            "changes": changes,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring package {package_id}: {str(e)}")
                await asyncio.sleep(self.update_interval)

    async def _search_provider(
        self, provider_id: str, criteria: SearchCriteria
    ) -> List[TravelPackage]:
        """
        Realizar búsqueda en un proveedor específico.
        """
        cache_key = f"search:{provider_id}:{criteria.dict()}"
        cached_results = self.cache.get(cache_key)

        if cached_results:
            return [TravelPackage(**pkg) for pkg in cached_results]

        provider = self.providers[provider_id]
        results = await provider.search_packages(criteria)

        if results:
            self.cache.set(
                cache_key, [pkg.dict() for pkg in results], ttl=self.update_interval
            )

        return results

    def _detect_changes(
        self, previous: TravelPackage, current: TravelPackage
    ) -> Dict[str, Any]:
        """
        Detectar cambios significativos entre versiones de un paquete.
        """
        changes = {}

        # Cambios en precio
        if previous.price != current.price:
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
