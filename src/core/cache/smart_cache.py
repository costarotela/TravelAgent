from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
from prometheus_client import Counter, Gauge
from src.utils.monitoring import METRICS

logger = logging.getLogger(__name__)

# Inicializar métricas
METRICS["cache_size"] = Gauge(
    "cache_size_bytes", "Size of cache in bytes", ["cache_type"]
)


class SmartCache:
    """
    Caché inteligente que adapta el TTL basado en patrones de cambio.
    """

    def __init__(self, default_ttl: int = 300):
        """
        Inicializa el caché.

        Args:
            default_ttl: Tiempo de vida por defecto en segundos
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl
        self._change_patterns: Dict[str, float] = {}
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

        if now > entry["expires_at"]:
            METRICS["cache_misses"].labels(cache_type="smart_cache").inc()
            del self._cache[key]
            return None

        METRICS["cache_hits"].labels(cache_type="smart_cache").inc()
        return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Almacena un valor en el caché.

        Args:
            key: Clave para almacenar
            value: Valor a almacenar
            ttl: Tiempo de vida en segundos (opcional)
        """
        if ttl is None:
            ttl = self._get_dynamic_ttl(key)

        expires_at = datetime.now() + timedelta(seconds=ttl)

        self._cache[key] = {
            "value": value,
            "expires_at": expires_at,
            "last_update": datetime.now(),
        }

        # Actualizar métricas
        METRICS["cache_size"].labels(cache_type="smart_cache").inc(len(str(value)))

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
        last_update = entry["last_update"]
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

    def clear_expired(self) -> None:
        """Elimina entradas expiradas del caché."""
        now = datetime.now()
        expired = [
            key for key, entry in self._cache.items() if now > entry["expires_at"]
        ]

        for key in expired:
            del self._cache[key]
            if key in self._change_patterns:
                del self._change_patterns[key]
