"""
Gestor de caché avanzado con soporte para múltiples backends.
"""

import json
import pickle
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta
import hashlib
import logging
from abc import ABC, abstractmethod
import asyncio
import aioredis
from diskcache import Cache
from ..config import config

class CacheBackend(ABC):
    """Interfaz base para backends de caché."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Obtener valor de caché."""
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
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

class RedisBackend(CacheBackend):
    """Backend de caché usando Redis."""
    
    def __init__(self, redis_config: Dict[str, Any]):
        self.redis = aioredis.from_url(
            f"redis://{redis_config['host']}:{redis_config['port']}",
            db=redis_config['db'],
            encoding="utf-8",
            decode_responses=False
        )
    
    async def get(self, key: str) -> Optional[Any]:
        """Obtener valor de Redis."""
        value = await self.redis.get(key)
        if value is None:
            return None
        return pickle.loads(value)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Guardar valor en Redis."""
        value = pickle.dumps(value)
        if ttl:
            await self.redis.setex(key, ttl, value)
        else:
            await self.redis.set(key, value)
    
    async def delete(self, key: str) -> None:
        """Eliminar valor de Redis."""
        await self.redis.delete(key)
    
    async def clear(self) -> None:
        """Limpiar toda la caché de Redis."""
        await self.redis.flushdb()
    
    async def exists(self, key: str) -> bool:
        """Verificar si existe una clave en Redis."""
        return await self.redis.exists(key) > 0

class DiskBackend(CacheBackend):
    """Backend de caché usando almacenamiento en disco."""
    
    def __init__(self, cache_dir: str):
        self.cache = Cache(cache_dir)
    
    async def get(self, key: str) -> Optional[Any]:
        """Obtener valor del disco."""
        return self.cache.get(key)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Guardar valor en disco."""
        if ttl:
            self.cache.set(key, value, expire=ttl)
        else:
            self.cache.set(key, value)
    
    async def delete(self, key: str) -> None:
        """Eliminar valor del disco."""
        self.cache.delete(key)
    
    async def clear(self) -> None:
        """Limpiar toda la caché del disco."""
        self.cache.clear()
    
    async def exists(self, key: str) -> bool:
        """Verificar si existe una clave en disco."""
        return key in self.cache

class MemoryBackend(CacheBackend):
    """Backend de caché en memoria."""
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.expiry: Dict[str, datetime] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Obtener valor de memoria."""
        if key not in self.cache:
            return None
        
        if key in self.expiry:
            if datetime.now() > self.expiry[key]:
                del self.cache[key]
                del self.expiry[key]
                return None
        
        return self.cache[key]
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Guardar valor en memoria."""
        self.cache[key] = value
        if ttl:
            self.expiry[key] = datetime.now() + timedelta(seconds=ttl)
    
    async def delete(self, key: str) -> None:
        """Eliminar valor de memoria."""
        self.cache.pop(key, None)
        self.expiry.pop(key, None)
    
    async def clear(self) -> None:
        """Limpiar toda la caché de memoria."""
        self.cache.clear()
        self.expiry.clear()
    
    async def exists(self, key: str) -> bool:
        """Verificar si existe una clave en memoria."""
        return key in self.cache

class CacheManager:
    """
    Gestor de caché avanzado con múltiples niveles.
    
    Características:
    1. Múltiples backends (Redis, Disco, Memoria)
    2. Políticas de caché configurables
    3. Compresión automática
    4. Métricas y monitoreo
    5. Limpieza automática
    """
    
    def __init__(self):
        """Inicializar gestor de caché."""
        self.logger = logging.getLogger(__name__)
        
        # Configurar backends
        self.backends: Dict[str, CacheBackend] = {}
        self._setup_backends()
        
        # Métricas
        self.hits = 0
        self.misses = 0
        self.total_size = 0
        
        # Configuración
        self.default_ttl = config.cache.ttl
        self.compression_threshold = 1024  # 1KB
    
    def _setup_backends(self) -> None:
        """Configurar backends de caché."""
        # Memoria siempre disponible
        self.backends["memory"] = MemoryBackend()
        
        # Redis si está configurado
        if config.cache.type == "redis":
            try:
                self.backends["redis"] = RedisBackend(config.cache.__dict__)
                self.logger.info("Redis cache backend initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Redis: {e}")
        
        # Disco siempre como fallback
        cache_dir = config.base_path / "cache"
        cache_dir.mkdir(exist_ok=True)
        self.backends["disk"] = DiskBackend(str(cache_dir))
    
    def _get_backend(self, key: str) -> CacheBackend:
        """Seleccionar backend apropiado."""
        if "redis" in self.backends:
            return self.backends["redis"]
        if key.startswith("large:"):
            return self.backends["disk"]
        return self.backends["memory"]
    
    def _compress_value(self, value: Any) -> bytes:
        """Comprimir valor si es necesario."""
        serialized = pickle.dumps(value)
        if len(serialized) > self.compression_threshold:
            import zlib
            return zlib.compress(serialized)
        return serialized
    
    def _decompress_value(self, value: bytes) -> Any:
        """Descomprimir valor si es necesario."""
        try:
            import zlib
            return pickle.loads(zlib.decompress(value))
        except:
            return pickle.loads(value)
    
    def _generate_key(self, key: str, namespace: Optional[str] = None) -> str:
        """Generar clave de caché."""
        if namespace:
            key = f"{namespace}:{key}"
        return hashlib.md5(key.encode()).hexdigest()
    
    async def get(
        self,
        key: str,
        default: Any = None,
        namespace: Optional[str] = None
    ) -> Any:
        """
        Obtener valor de caché.
        
        Args:
            key: Clave a buscar
            default: Valor por defecto si no existe
            namespace: Namespace opcional
        
        Returns:
            Valor almacenado o default
        """
        cache_key = self._generate_key(key, namespace)
        backend = self._get_backend(cache_key)
        
        try:
            value = await backend.get(cache_key)
            if value is not None:
                self.hits += 1
                if isinstance(value, bytes):
                    value = self._decompress_value(value)
                return value
            
            self.misses += 1
            return default
            
        except Exception as e:
            self.logger.error(f"Cache get error: {e}")
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None
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
        backend = self._get_backend(cache_key)
        
        try:
            # Comprimir valores grandes
            if isinstance(value, (dict, list)) and len(str(value)) > self.compression_threshold:
                value = self._compress_value(value)
            
            await backend.set(
                cache_key,
                value,
                ttl or self.default_ttl
            )
            
            # Actualizar métricas
            self.total_size += len(str(value))
            
        except Exception as e:
            self.logger.error(f"Cache set error: {e}")
    
    async def delete(
        self,
        key: str,
        namespace: Optional[str] = None
    ) -> None:
        """
        Eliminar valor de caché.
        
        Args:
            key: Clave a eliminar
            namespace: Namespace opcional
        """
        cache_key = self._generate_key(key, namespace)
        backend = self._get_backend(cache_key)
        
        try:
            await backend.delete(cache_key)
        except Exception as e:
            self.logger.error(f"Cache delete error: {e}")
    
    async def clear(
        self,
        namespace: Optional[str] = None
    ) -> None:
        """
        Limpiar caché.
        
        Args:
            namespace: Si se especifica, solo limpia ese namespace
        """
        if namespace:
            pattern = self._generate_key("*", namespace)
            for backend in self.backends.values():
                keys = await backend.get_keys(pattern)
                for key in keys:
                    await backend.delete(key)
        else:
            for backend in self.backends.values():
                await backend.clear()
        
        # Resetear métricas
        self.hits = 0
        self.misses = 0
        self.total_size = 0
    
    async def exists(
        self,
        key: str,
        namespace: Optional[str] = None
    ) -> bool:
        """
        Verificar si existe una clave.
        
        Args:
            key: Clave a verificar
            namespace: Namespace opcional
        
        Returns:
            True si existe, False si no
        """
        cache_key = self._generate_key(key, namespace)
        backend = self._get_backend(cache_key)
        
        try:
            return await backend.exists(cache_key)
        except Exception as e:
            self.logger.error(f"Cache exists error: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Union[int, float]]:
        """
        Obtener métricas de caché.
        
        Returns:
            Dict con métricas
        """
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_size": self.total_size,
            "backends": list(self.backends.keys())
        }

# Instancia global
cache_manager = CacheManager()
