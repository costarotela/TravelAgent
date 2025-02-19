from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
import zlib
import json
import sys
from prometheus_client import Counter, Gauge, Histogram
from src.utils.monitoring import METRICS

logger = logging.getLogger(__name__)

# Inicializar métricas
METRICS["cache_size"] = Gauge(
    "cache_size_bytes", "Size of cache in bytes", ["cache_type"]
)
METRICS["cache_compression_ratio"] = Histogram(
    "cache_compression_ratio", "Compression ratio of cached data", ["cache_type"]
)
METRICS["cache_entry_size"] = Histogram(
    "cache_entry_size_bytes", "Size of individual cache entries", ["cache_type"]
)
METRICS["cache_memory_usage"] = Gauge(
    "cache_memory_usage_bytes", "Total memory usage of cache", ["cache_type"]
)
METRICS["cache_cleanup_time"] = Histogram(
    "cache_cleanup_time_seconds", "Time taken for cache cleanup", ["cache_type"]
)


class CacheEntry:
    """Entrada de caché con metadatos."""

    def __init__(
        self,
        value: Any,
        expires_at: datetime,
        priority: int = 1,
        compress: bool = False,
    ):
        """
        Inicializa una entrada de caché.

        Args:
            value: Valor a almacenar
            expires_at: Fecha de expiración
            priority: Prioridad (1-5, siendo 5 la más alta)
            compress: Si se debe comprimir el valor
        """
        self.priority = max(1, min(5, priority))
        self.expires_at = expires_at
        self.last_access = datetime.now()
        self.access_count = 0

        # Comprimir datos si es necesario
        if compress and isinstance(value, (dict, list)):
            json_data = json.dumps(value).encode("utf-8")
            self.compressed = True
            self.value = zlib.compress(json_data)
            self.original_size = len(json_data)
            self.compressed_size = len(self.value)
        else:
            self.compressed = False
            self.value = value
            self.original_size = sys.getsizeof(value)
            self.compressed_size = self.original_size


class SmartCache:
    """
    Caché inteligente con priorización y compresión automática.
    """

    def __init__(
        self,
        default_ttl: int = 300,
        max_size_mb: int = 100,
        compression_threshold_kb: int = 100,
    ):
        """
        Inicializa el caché.

        Args:
            default_ttl: Tiempo de vida por defecto en segundos
            max_size_mb: Tamaño máximo del caché en MB
            compression_threshold_kb: Tamaño en KB a partir del cual comprimir
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._change_patterns: Dict[str, float] = {}
        self._max_size = max_size_mb * 1024 * 1024  # Convertir a bytes
        self._compression_threshold = (
            compression_threshold_kb * 1024
        )  # Convertir a bytes
        self.logger = logging.getLogger(__name__)

    def get(self, key: str) -> Optional[Any]:
        """
        Obtiene un valor del caché.

        Args:
            key: Clave a buscar

        Returns:
            Valor almacenado o None si no existe o expiró
        """
        if key not in self._cache:
            METRICS["cache_misses"].labels(cache_type="smart_cache").inc()
            return None

        entry = self._cache[key]
        now = datetime.now()

        if now > entry.expires_at:
            METRICS["cache_misses"].labels(cache_type="smart_cache").inc()
            del self._cache[key]
            return None

        # Actualizar estadísticas de acceso
        entry.last_access = now
        entry.access_count += 1

        METRICS["cache_hits"].labels(cache_type="smart_cache").inc()

        # Descomprimir si es necesario
        if entry.compressed:
            json_data = zlib.decompress(entry.value).decode("utf-8")
            return json.loads(json_data)

        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        priority: int = 1,
    ) -> None:
        """
        Almacena un valor en el caché.

        Args:
            key: Clave para almacenar
            value: Valor a almacenar
            ttl: Tiempo de vida en segundos (opcional)
            priority: Prioridad del valor (1-5)
        """
        if ttl is None:
            ttl = self._get_dynamic_ttl(key)

        expires_at = datetime.now() + timedelta(seconds=ttl)

        # Determinar si se debe comprimir
        value_size = sys.getsizeof(value)
        should_compress = value_size > self._compression_threshold

        # Crear entrada
        entry = CacheEntry(value, expires_at, priority, compress=should_compress)

        # Verificar espacio disponible
        if self._get_total_size() + entry.compressed_size > self._max_size:
            self._cleanup_by_size(entry.compressed_size)

        self._cache[key] = entry

        # Actualizar métricas
        METRICS["cache_size"].labels(cache_type="smart_cache").set(
            self._get_total_size()
        )
        if entry.compressed:
            ratio = entry.original_size / entry.compressed_size
            METRICS["cache_compression_ratio"].labels(cache_type="smart_cache").observe(
                ratio
            )
        METRICS["cache_entry_size"].labels(cache_type="smart_cache").observe(
            entry.compressed_size
        )

    def _get_total_size(self) -> int:
        """
        Calcula el tamaño total del caché.

        Returns:
            Tamaño en bytes
        """
        return sum(entry.compressed_size for entry in self._cache.values())

    def _cleanup_by_size(self, needed_space: int) -> None:
        """
        Limpia el caché para hacer espacio.

        Args:
            needed_space: Espacio necesario en bytes
        """
        start_time = datetime.now()

        # Ordenar entradas por prioridad (menor) y último acceso (más antiguo)
        entries = sorted(
            self._cache.items(),
            key=lambda x: (x[1].priority, x[1].last_access, -x[1].access_count),
        )

        freed_space = 0
        for key, entry in entries:
            if freed_space >= needed_space:
                break
            freed_space += entry.compressed_size
            del self._cache[key]
            if key in self._change_patterns:
                del self._change_patterns[key]

        cleanup_time = (datetime.now() - start_time).total_seconds()
        METRICS["cache_cleanup_time"].labels(cache_type="smart_cache").observe(
            cleanup_time
        )
        self.logger.info(
            f"Limpieza de caché completada en {cleanup_time:.2f}s, liberado {freed_space} bytes"
        )

    def _get_dynamic_ttl(self, key: str) -> int:
        """
        Calcula el TTL dinámico basado en patrones de cambio.

        Args:
            key: Clave del valor

        Returns:
            TTL en segundos
        """
        if key not in self._change_patterns:
            return self._default_ttl

        # Ajustar TTL basado en frecuencia de cambios
        change_frequency = self._change_patterns[key]

        # Si los cambios son muy frecuentes, reducir TTL
        if change_frequency < 60:  # Cambios cada minuto
            return min(60, self._default_ttl)
        # Si los cambios son poco frecuentes, aumentar TTL
        elif change_frequency > 3600:  # Cambios cada hora
            return min(3600, self._default_ttl * 2)

        return self._default_ttl

    def update_change_pattern(self, key: str, changed: bool) -> None:
        """
        Actualiza el patrón de cambios para una clave.

        Args:
            key: Clave a actualizar
            changed: Si el valor cambió
        """
        if key not in self._cache:
            return

        entry = self._cache[key]
        last_update = entry.last_access
        now = datetime.now()

        if changed:
            # Calcular tiempo desde última actualización
            time_since_update = (now - last_update).total_seconds()

            # Actualizar patrón de cambios
            if key in self._change_patterns:
                # Promedio móvil
                self._change_patterns[key] = (
                    self._change_patterns[key] * 0.7 + time_since_update * 0.3
                )
            else:
                self._change_patterns[key] = time_since_update

            self.logger.info(
                f"Patrón de cambios actualizado para {key}: "
                f"cada {self._change_patterns[key]:.1f}s"
            )

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del caché.

        Returns:
            Diccionario con estadísticas
        """
        total_entries = len(self._cache)
        total_size = self._get_total_size()
        compressed_entries = sum(
            1 for entry in self._cache.values() if entry.compressed
        )

        return {
            "total_entries": total_entries,
            "total_size_bytes": total_size,
            "compressed_entries": compressed_entries,
            "memory_usage_percent": (total_size / self._max_size) * 100,
            "average_entry_size": (
                total_size / total_entries if total_entries > 0 else 0
            ),
        }
