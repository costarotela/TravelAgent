"""Motor de búsqueda simplificado."""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor

from src.core.providers import TravelProvider, SearchCriteria, TravelPackage
from src.utils.monitoring import monitor
from src.utils.cache import search_cache

logger = logging.getLogger(__name__)


class SearchError(Exception):
    """Error base para búsquedas."""

    pass


class ProviderError(SearchError):
    """Error específico de proveedor."""

    def __init__(self, provider: str, original_error: Exception):
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"Error en proveedor {provider}: {str(original_error)}")


class SearchEngine:
    """Motor de búsqueda simplificado."""

    def __init__(self, providers: List[TravelProvider]):
        """Inicializar motor con proveedores."""
        self.providers = providers
        self._executor = ThreadPoolExecutor(max_workers=3)

    async def _search_provider(
        self,
        provider: TravelProvider,
        criteria: SearchCriteria,
        progress_callback: Optional[callable] = None,
    ) -> List[TravelPackage]:
        """Buscar en un proveedor específico con manejo de errores."""
        try:
            # Notificar inicio de búsqueda
            if progress_callback:
                progress_callback(f"Iniciando búsqueda en {provider.name}...")

            # Buscar en caché primero
            cache_key = {
                "provider": provider.name,
                "origin": criteria.origin,
                "destination": criteria.destination,
                "departure_date": criteria.departure_date.isoformat(),
                "adults": criteria.adults,
            }

            cached_results = search_cache.get_search_results(cache_key)
            if cached_results:
                logger.info(f"Resultados encontrados en caché para {provider.name}")
                monitor.log_metric("cache_hit", 1, {"provider": provider.name})
                if progress_callback:
                    progress_callback(
                        f"Resultados encontrados en caché para {provider.name}"
                    )
                return cached_results

            # Buscar en el proveedor
            if progress_callback:
                progress_callback(f"Buscando en {provider.name}...")

            results = await provider.search_packages(criteria)

            # Guardar en caché
            if results:
                search_cache.cache_search_results(cache_key, results)
                monitor.log_metric(
                    "search_success",
                    1,
                    {"provider": provider.name, "results": len(results)},
                )

            if progress_callback:
                progress_callback(
                    f"Búsqueda completada en {provider.name}: "
                    f"{len(results)} resultados encontrados"
                )

            return results

        except Exception as e:
            logger.error(f"Error en proveedor {provider.name}: {str(e)}")
            monitor.log_error(
                e,
                {
                    "provider": provider.name,
                    "action": "search",
                    "criteria": str(criteria),
                },
            )
            raise ProviderError(provider.name, e)

    async def search(
        self, criteria: SearchCriteria, progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Realizar búsqueda en todos los proveedores.

        Args:
            criteria: Criterios de búsqueda
            progress_callback: Función opcional para reportar progreso

        Returns:
            Dict con resultados y errores por proveedor
        """
        start_time = datetime.now()
        all_results = []
        errors = {}

        # Validar criterios
        if not criteria.is_valid():
            raise SearchError("Criterios de búsqueda inválidos")

        # Buscar en paralelo en todos los proveedores
        tasks = []
        for provider in self.providers:
            task = asyncio.create_task(
                self._search_provider(provider, criteria, progress_callback)
            )
            tasks.append((provider.name, task))

        # Esperar resultados
        for provider_name, task in tasks:
            try:
                results = await task
                if results:
                    all_results.extend(results)
            except ProviderError as e:
                errors[provider_name] = str(e.original_error)
                if progress_callback:
                    progress_callback(
                        f"Error en {provider_name}: {str(e.original_error)}"
                    )

        # Registrar métricas
        duration = (datetime.now() - start_time).total_seconds()
        monitor.log_metric("search_duration", duration)
        monitor.log_metric("total_results", len(all_results))
        monitor.log_metric("provider_errors", len(errors))

        if progress_callback:
            progress_callback(
                f"Búsqueda completada en {duration:.1f}s. "
                f"Encontrados {len(all_results)} resultados."
            )

        return {
            "results": all_results,
            "errors": errors,
            "stats": {
                "duration": duration,
                "total_results": len(all_results),
                "providers_with_errors": len(errors),
            },
        }
