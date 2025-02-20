"""
Colector base para extracción de datos.

Este módulo implementa:
1. Funcionalidad base de recolección
2. Manejo de rate limiting
3. Sistema de caché
4. Control de errores
"""

from typing import Dict, Any, Optional, List, Type
from datetime import datetime, timedelta
import logging
import asyncio
from abc import ABC, abstractmethod
from prometheus_client import Counter, Histogram
import aiohttp
import cachetools
from ratelimit import limits, sleep_and_retry

from ..schemas import DataSource, CollectionResult, CacheConfig, RateLimitConfig
from ..metrics import get_metrics_collector

# Métricas
COLLECTION_OPERATIONS = Counter(
    "collection_operations_total",
    "Number of collection operations",
    ["collector_type", "status"],
)

COLLECTION_LATENCY = Histogram(
    "collection_operation_latency_seconds",
    "Latency of collection operations",
    ["collector_type"],
)


class BaseCollector(ABC):
    """
    Colector base.

    Responsabilidades:
    1. Definir interfaz común
    2. Manejar rate limiting
    3. Gestionar caché
    4. Controlar errores
    """

    def __init__(
        self,
        source: DataSource,
        cache_config: Optional[CacheConfig] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        """
        Inicializar colector.

        Args:
            source: Fuente de datos
            cache_config: Configuración de caché
            rate_limit_config: Configuración de rate limiting
        """
        self.logger = logging.getLogger(__name__)
        self.metrics = get_metrics_collector()
        self.source = source

        # Configuración por defecto
        self.cache_config = cache_config or CacheConfig(
            ttl=300, max_size=1000  # 5 minutos
        )

        self.rate_limit_config = rate_limit_config or RateLimitConfig(
            calls=60, period=60  # 60 llamadas por minuto
        )

        # Inicializar caché
        self.cache = cachetools.TTLCache(
            maxsize=self.cache_config.max_size, ttl=self.cache_config.ttl
        )

        # Cliente HTTP
        self.session: Optional[aiohttp.ClientSession] = None

        # Semáforo para rate limiting
        self.semaphore = asyncio.Semaphore(self.rate_limit_config.calls)

    async def __aenter__(self):
        """Iniciar sesión HTTP."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cerrar sesión HTTP."""
        if self.session:
            await self.session.close()

    @abstractmethod
    async def collect(self, params: Dict[str, Any]) -> CollectionResult:
        """
        Recolectar datos.

        Args:
            params: Parámetros de recolección

        Returns:
            Resultado de recolección
        """
        pass

    async def get_data(
        self, params: Dict[str, Any], force_refresh: bool = False
    ) -> CollectionResult:
        """
        Obtener datos con caché.

        Args:
            params: Parámetros de recolección
            force_refresh: Forzar actualización

        Returns:
            Resultado de recolección
        """
        try:
            start_time = datetime.now()

            # Generar clave de caché
            cache_key = self._generate_cache_key(params)

            # Verificar caché
            if not force_refresh and cache_key in self.cache:
                COLLECTION_OPERATIONS.labels(
                    collector_type=self.source.type, status="cache_hit"
                ).inc()

                return self.cache[cache_key]

            # Aplicar rate limiting
            async with self.semaphore:
                # Recolectar datos
                result = await self.collect(params)

                # Actualizar caché si fue exitoso
                if result.success:
                    self.cache[cache_key] = result

                # Registrar métricas
                COLLECTION_OPERATIONS.labels(
                    collector_type=self.source.type,
                    status="success" if result.success else "error",
                ).inc()

                duration = (datetime.now() - start_time).total_seconds()
                COLLECTION_LATENCY.labels(collector_type=self.source.type).observe(
                    duration
                )

                return result

        except Exception as e:
            self.logger.error(f"Error obteniendo datos: {e}")
            return CollectionResult(success=False, error=str(e))

    async def clear_cache(self, params: Optional[Dict[str, Any]] = None) -> None:
        """
        Limpiar caché.

        Args:
            params: Parámetros específicos o None para limpiar todo
        """
        try:
            if params:
                cache_key = self._generate_cache_key(params)
                if cache_key in self.cache:
                    del self.cache[cache_key]
            else:
                self.cache.clear()

        except Exception as e:
            self.logger.error(f"Error limpiando caché: {e}")

    def _generate_cache_key(self, params: Dict[str, Any]) -> str:
        """Generar clave de caché."""
        try:
            # Ordenar parámetros para consistencia
            sorted_params = sorted(params.items(), key=lambda x: x[0])

            # Generar clave única
            return f"{self.source.type}:{str(sorted_params)}"

        except Exception as e:
            self.logger.error(f"Error generando clave: {e}")
            return str(datetime.now().timestamp())

    @sleep_and_retry
    @limits(calls=60, period=60)
    async def _rate_limited_request(
        self, url: str, method: str = "GET", **kwargs
    ) -> aiohttp.ClientResponse:
        """
        Realizar request con rate limiting.

        Args:
            url: URL del request
            method: Método HTTP
            **kwargs: Argumentos adicionales

        Returns:
            Respuesta del request
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        return await self.session.request(method, url, **kwargs)

    async def _handle_response(
        self, response: aiohttp.ClientResponse
    ) -> Dict[str, Any]:
        """
        Procesar respuesta HTTP.

        Args:
            response: Respuesta HTTP

        Returns:
            Datos procesados
        """
        try:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Error {response.status}: {response.reason}")

        except Exception as e:
            self.logger.error(f"Error procesando respuesta: {e}")
            raise


# Registro de colectores
collectors: Dict[str, Type[BaseCollector]] = {}
