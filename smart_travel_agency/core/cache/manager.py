"""
Sistema avanzado de caché con soporte para optimización.

Este módulo implementa:
1. Caché multi-nivel (Redis, Disco, Memoria)
2. Optimización de almacenamiento
3. Métricas detalladas
4. Políticas de expiración inteligentes
"""

import json
import pickle
import zlib
from typing import Any, Dict, Optional, Union, List
from datetime import datetime, timedelta
import hashlib
import logging
from abc import ABC, abstractmethod
import asyncio
import aioredis
from diskcache import Cache
from prometheus_client import Counter, Histogram, Gauge

# Métricas
CACHE_OPERATIONS = Counter(
    "cache_operations_total",
    "Number of cache operations",
    ["operation", "backend", "result"],
)

CACHE_SIZE = Gauge("cache_size_bytes", "Size of cached data in bytes", ["backend"])

CACHE_LATENCY = Histogram(
    "cache_operation_latency_seconds",
    "Latency of cache operations",
    ["operation", "backend"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5],
)


class CacheBackend(ABC):
    """Interfaz base para backends de caché."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Obtener valor de caché."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Guardar valor en caché."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Eliminar valor de caché."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Limpiar toda la caché."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Verificar si existe una clave."""
        pass

    @abstractmethod
    async def get_size(self) -> int:
        """Obtener tamaño total en bytes."""
        pass


class RedisBackend(CacheBackend):
    """Backend de caché usando Redis."""

    def __init__(self, redis_config: Dict[str, Any]):
        """
        Inicializar backend de Redis.

        Args:
            redis_config: Configuración de conexión
        """
        self.redis = aioredis.from_url(
            f"redis://{redis_config['host']}:{redis_config['port']}",
            db=redis_config["db"],
            encoding="utf-8",
            decode_responses=False,
        )
        self.name = "redis"

    async def get(self, key: str) -> Optional[Any]:
        """Obtener valor de Redis."""
        start_time = datetime.now()
        try:
            value = await self.redis.get(key)
            if value is None:
                CACHE_OPERATIONS.labels(
                    operation="get", backend=self.name, result="miss"
                ).inc()
                return None

            CACHE_OPERATIONS.labels(
                operation="get", backend=self.name, result="hit"
            ).inc()
            return pickle.loads(value)

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            CACHE_LATENCY.labels(operation="get", backend=self.name).observe(duration)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Guardar valor en Redis."""
        start_time = datetime.now()
        try:
            value = pickle.dumps(value)
            if ttl:
                await self.redis.setex(key, ttl, value)
            else:
                await self.redis.set(key, value)

            CACHE_OPERATIONS.labels(
                operation="set", backend=self.name, result="success"
            ).inc()

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            CACHE_LATENCY.labels(operation="set", backend=self.name).observe(duration)

    async def delete(self, key: str) -> None:
        """Eliminar valor de Redis."""
        await self.redis.delete(key)
        CACHE_OPERATIONS.labels(
            operation="delete", backend=self.name, result="success"
        ).inc()

    async def clear(self) -> None:
        """Limpiar toda la caché de Redis."""
        await self.redis.flushdb()
        CACHE_OPERATIONS.labels(
            operation="clear", backend=self.name, result="success"
        ).inc()

    async def exists(self, key: str) -> bool:
        """Verificar si existe una clave en Redis."""
        return await self.redis.exists(key) > 0

    async def get_size(self) -> int:
        """Obtener tamaño total en bytes."""
        info = await self.redis.info("memory")
        return info["used_memory"]


class DiskBackend(CacheBackend):
    """Backend de caché usando almacenamiento en disco."""

    def __init__(self, cache_dir: str):
        """
        Inicializar backend de disco.

        Args:
            cache_dir: Directorio para almacenar caché
        """
        self.cache = Cache(cache_dir)
        self.name = "disk"

    async def get(self, key: str) -> Optional[Any]:
        """Obtener valor del disco."""
        start_time = datetime.now()
        try:
            value = self.cache.get(key)
            CACHE_OPERATIONS.labels(
                operation="get",
                backend=self.name,
                result="hit" if value is not None else "miss",
            ).inc()
            return value

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            CACHE_LATENCY.labels(operation="get", backend=self.name).observe(duration)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Guardar valor en disco."""
        start_time = datetime.now()
        try:
            self.cache.set(key, value, expire=ttl)
            CACHE_OPERATIONS.labels(
                operation="set", backend=self.name, result="success"
            ).inc()

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            CACHE_LATENCY.labels(operation="set", backend=self.name).observe(duration)

    async def delete(self, key: str) -> None:
        """Eliminar valor del disco."""
        self.cache.delete(key)
        CACHE_OPERATIONS.labels(
            operation="delete", backend=self.name, result="success"
        ).inc()

    async def clear(self) -> None:
        """Limpiar toda la caché del disco."""
        self.cache.clear()
        CACHE_OPERATIONS.labels(
            operation="clear", backend=self.name, result="success"
        ).inc()

    async def exists(self, key: str) -> bool:
        """Verificar si existe una clave en disco."""
        return key in self.cache

    async def get_size(self) -> int:
        """Obtener tamaño total en bytes."""
        return self.cache.volume()


class MemoryBackend(CacheBackend):
    """Backend de caché en memoria."""

    def __init__(self):
        """Inicializar backend de memoria."""
        self.cache: Dict[str, Any] = {}
        self.expiry: Dict[str, datetime] = {}
        self.name = "memory"

    async def get(self, key: str) -> Optional[Any]:
        """Obtener valor de memoria."""
        start_time = datetime.now()
        try:
            if key not in self.cache:
                CACHE_OPERATIONS.labels(
                    operation="get", backend=self.name, result="miss"
                ).inc()
                return None

            if key in self.expiry and datetime.now() > self.expiry[key]:
                await self.delete(key)
                return None

            CACHE_OPERATIONS.labels(
                operation="get", backend=self.name, result="hit"
            ).inc()
            return self.cache[key]

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            CACHE_LATENCY.labels(operation="get", backend=self.name).observe(duration)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Guardar valor en memoria."""
        start_time = datetime.now()
        try:
            self.cache[key] = value
            if ttl:
                self.expiry[key] = datetime.now() + timedelta(seconds=ttl)

            CACHE_OPERATIONS.labels(
                operation="set", backend=self.name, result="success"
            ).inc()

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            CACHE_LATENCY.labels(operation="set", backend=self.name).observe(duration)

    async def delete(self, key: str) -> None:
        """Eliminar valor de memoria."""
        self.cache.pop(key, None)
        self.expiry.pop(key, None)
        CACHE_OPERATIONS.labels(
            operation="delete", backend=self.name, result="success"
        ).inc()

    async def clear(self) -> None:
        """Limpiar toda la caché de memoria."""
        self.cache.clear()
        self.expiry.clear()
        CACHE_OPERATIONS.labels(
            operation="clear", backend=self.name, result="success"
        ).inc()

    async def exists(self, key: str) -> bool:
        """Verificar si existe una clave en memoria."""
        if key not in self.cache:
            return False

        if key in self.expiry and datetime.now() > self.expiry[key]:
            asyncio.create_task(self.delete(key))
            return False

        return True

    async def get_size(self) -> int:
        """Obtener tamaño total en bytes."""
        return sum(len(pickle.dumps(v)) for v in self.cache.values())


class CacheManager:
    """
    Gestor de caché avanzado con múltiples niveles y optimización.
    """

    def __init__(self):
        """Inicializar gestor de caché."""
        self.logger = logging.getLogger(__name__)

        # Configurar backends
        self.backends: Dict[str, CacheBackend] = {}
        self._setup_backends()

        # Configuración
        self.default_ttl = 3600  # 1 hora
        self.compression_threshold = 1024  # 1KB

        # Iniciar tarea de limpieza
        asyncio.create_task(self._cleanup_task())

    def _setup_backends(self):
        """Configurar backends de caché."""
        # Configuración de Redis
        redis_config = {"host": "localhost", "port": 6379, "db": 0}

        self.backends["redis"] = RedisBackend(redis_config)
        self.backends["disk"] = DiskBackend("/tmp/smart_travel_cache")
        self.backends["memory"] = MemoryBackend()

    def _get_backend(self, key: str) -> CacheBackend:
        """
        Seleccionar backend apropiado.

        Args:
            key: Clave a almacenar

        Returns:
            Backend más apropiado
        """
        # Por ahora una selección simple
        if key.startswith("session:"):
            return self.backends["redis"]
        elif key.startswith("static:"):
            return self.backends["disk"]
        else:
            return self.backends["memory"]

    def _compress_value(self, value: Any) -> bytes:
        """Comprimir valor si es necesario."""
        data = pickle.dumps(value)
        if len(data) > self.compression_threshold:
            return zlib.compress(data)
        return data

    def _decompress_value(self, value: bytes) -> Any:
        """Descomprimir valor si es necesario."""
        try:
            return pickle.loads(zlib.decompress(value))
        except zlib.error:
            return pickle.loads(value)

    def _generate_key(self, key: str, namespace: Optional[str] = None) -> str:
        """Generar clave de caché."""
        if namespace:
            key = f"{namespace}:{key}"
        return hashlib.sha256(key.encode()).hexdigest()

    async def get(
        self, key: str, default: Any = None, namespace: Optional[str] = None
    ) -> Any:
        """
        Obtener valor de caché.

        Args:
            key: Clave a buscar
            default: Valor por defecto
            namespace: Namespace opcional

        Returns:
            Valor almacenado o default
        """
        cache_key = self._generate_key(key, namespace)
        backend = self._get_backend(key)

        value = await backend.get(cache_key)
        if value is None:
            return default

        return self._decompress_value(value)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
    ) -> None:
        """
        Guardar valor en caché.

        Args:
            key: Clave para almacenar
            value: Valor a almacenar
            ttl: Tiempo de vida en segundos
            namespace: Namespace opcional
        """
        cache_key = self._generate_key(key, namespace)
        backend = self._get_backend(key)

        compressed = self._compress_value(value)
        await backend.set(cache_key, compressed, ttl or self.default_ttl)

        # Actualizar métricas de tamaño
        CACHE_SIZE.labels(backend=backend.name).set(await backend.get_size())

    async def delete(self, key: str, namespace: Optional[str] = None) -> None:
        """
        Eliminar valor de caché.

        Args:
            key: Clave a eliminar
            namespace: Namespace opcional
        """
        cache_key = self._generate_key(key, namespace)
        backend = self._get_backend(key)
        await backend.delete(cache_key)

    async def clear(self, namespace: Optional[str] = None) -> None:
        """
        Limpiar caché.

        Args:
            namespace: Si se especifica, solo limpia ese namespace
        """
        if namespace:
            # TODO: Implementar limpieza por namespace
            pass
        else:
            for backend in self.backends.values():
                await backend.clear()

    async def exists(self, key: str, namespace: Optional[str] = None) -> bool:
        """
        Verificar si existe una clave.

        Args:
            key: Clave a verificar
            namespace: Namespace opcional

        Returns:
            True si existe, False si no
        """
        cache_key = self._generate_key(key, namespace)
        backend = self._get_backend(key)
        return await backend.exists(cache_key)

    async def _cleanup_task(self):
        """Tarea periódica de limpieza."""
        while True:
            try:
                # Actualizar métricas de tamaño
                for backend in self.backends.values():
                    CACHE_SIZE.labels(backend=backend.name).set(
                        await backend.get_size()
                    )

                # Esperar 5 minutos
                await asyncio.sleep(300)

            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)


# Instancia global
cache_manager = CacheManager()


async def get_cache_manager() -> CacheManager:
    """Obtener instancia única del gestor."""
    return cache_manager
