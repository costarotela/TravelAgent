"""Módulo de caché simple usando TTLCache."""

from cachetools import TTLCache
from typing import Any, Optional, Dict
import hashlib
import json
from datetime import timedelta


class SimpleCache:
    """Caché simple en memoria con TTL."""

    def __init__(self, ttl: int = 3600, maxsize: int = 100):
        """
        Inicializar caché.

        Args:
            ttl: Tiempo de vida en segundos (default: 1 hora)
            maxsize: Tamaño máximo del caché (default: 100 items)
        """
        self.cache = TTLCache(maxsize=maxsize, ttl=ttl)

    def _generate_key(self, *args: Any, **kwargs: Any) -> str:
        """Generar clave única para los argumentos."""
        # Convertir args y kwargs a una representación consistente
        key_dict = {"args": args, "kwargs": {k: v for k, v in sorted(kwargs.items())}}

        # Convertir a JSON y generar hash
        key_str = json.dumps(key_dict, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Obtener valor del caché."""
        return self.cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """Guardar valor en el caché."""
        self.cache[key] = value

    def delete(self, key: str) -> None:
        """Eliminar valor del caché."""
        self.cache.pop(key, None)

    def clear(self) -> None:
        """Limpiar todo el caché."""
        self.cache.clear()


class SearchCache(SimpleCache):
    """Caché específico para búsquedas."""

    def __init__(self):
        """Inicializar con TTL de 15 minutos."""
        super().__init__(ttl=900, maxsize=50)  # 15 minutos, 50 búsquedas

    def get_search_results(self, criteria: Dict[str, Any]) -> Optional[Any]:
        """Obtener resultados de búsqueda cacheados."""
        key = self._generate_key(**criteria)
        return self.get(key)

    def cache_search_results(self, criteria: Dict[str, Any], results: Any) -> None:
        """Cachear resultados de búsqueda."""
        key = self._generate_key(**criteria)
        self.set(key, results)


# Instancias globales
search_cache = SearchCache()  # Para búsquedas
general_cache = SimpleCache()  # Para uso general
