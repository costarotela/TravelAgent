"""
Gestor de almacenamiento del agente de viajes.

Este módulo se encarga de:
1. Gestionar persistencia
2. Coordinar backups
3. Manejar caché
4. Optimizar acceso
"""

from typing import Dict, Any, Optional, List, Union
import logging
from datetime import datetime
import json
import os
import asyncio
from pathlib import Path

from .schemas import (
    TravelPackage,
    SearchCriteria,
    Provider,
    Booking,
    Budget,
    CacheConfig,
)
from ..memory.supabase import SupabaseMemory


class StorageManager:
    """Gestor de almacenamiento del agente de viajes."""

    def __init__(self):
        """Inicializar gestor."""
        self.logger = logging.getLogger(__name__)
        self.memory = SupabaseMemory()

        # Configuración
        self.config = {
            "cache_enabled": True,
            "cache_ttl": 3600,  # 1 hora
            "backup_interval": 86400,  # 24 horas
            "max_cache_size": 1024 * 1024 * 100,  # 100MB
        }

        # Estado del gestor
        self.active = False
        self.last_backup = None

        # Caché en memoria
        self.cache: Dict[str, Any] = {}
        self.cache_metadata: Dict[str, CacheConfig] = {}

    async def start(self):
        """Iniciar gestor."""
        try:
            self.active = True

            # Inicializar sistema de archivos
            await self._initialize_fs()

            # Cargar caché
            await self._load_cache()

            # Iniciar tareas de mantenimiento
            asyncio.create_task(self._maintenance_task())

            self.logger.info("Gestor de almacenamiento iniciado")

        except Exception as e:
            self.logger.error(f"Error iniciando gestor: {str(e)}")
            raise

    async def stop(self):
        """Detener gestor."""
        try:
            self.active = False

            # Guardar caché
            await self._save_cache()

            # Realizar backup final
            await self._backup()

            self.logger.info("Gestor de almacenamiento detenido")

        except Exception as e:
            self.logger.error(f"Error deteniendo gestor: {str(e)}")
            raise

    async def store(
        self,
        key: str,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None,
        cache: bool = True,
    ):
        """
        Almacenar datos.

        Args:
            key: Clave de almacenamiento
            data: Datos a almacenar
            metadata: Metadatos adicionales
            cache: Usar caché
        """
        try:
            # Preparar datos
            storage_data = {
                "key": key,
                "data": data,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat(),
            }

            # Almacenar en memoria si caché está habilitado
            if cache and self.config["cache_enabled"]:
                await self._store_cache(key, storage_data)

            # Almacenar en base de conocimiento
            await self.memory.store_data(storage_data)

        except Exception as e:
            self.logger.error(f"Error almacenando datos: {str(e)}")
            raise

    async def retrieve(self, key: str, use_cache: bool = True) -> Optional[Any]:
        """
        Recuperar datos.

        Args:
            key: Clave de almacenamiento
            use_cache: Usar caché

        Returns:
            Datos almacenados
        """
        try:
            # Verificar caché
            if use_cache and self.config["cache_enabled"]:
                cached_data = await self._get_cache(key)
                if cached_data:
                    return cached_data["data"]

            # Obtener de base de conocimiento
            data = await self.memory.get_data(key)
            if data:
                # Actualizar caché
                if self.config["cache_enabled"]:
                    await self._store_cache(key, data)
                return data["data"]

            return None

        except Exception as e:
            self.logger.error(f"Error recuperando datos: {str(e)}")
            return None

    async def delete(self, key: str):
        """
        Eliminar datos.

        Args:
            key: Clave de almacenamiento
        """
        try:
            # Eliminar de caché
            if self.config["cache_enabled"]:
                await self._delete_cache(key)

            # Eliminar de base de conocimiento
            await self.memory.delete_data(key)

        except Exception as e:
            self.logger.error(f"Error eliminando datos: {str(e)}")
            raise

    async def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """
        Listar claves almacenadas.

        Args:
            pattern: Patrón de búsqueda

        Returns:
            Lista de claves
        """
        try:
            # Obtener claves de base de conocimiento
            keys = await self.memory.list_keys(pattern)

            return keys

        except Exception as e:
            self.logger.error(f"Error listando claves: {str(e)}")
            return []

    async def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Obtener metadatos.

        Args:
            key: Clave de almacenamiento

        Returns:
            Metadatos almacenados
        """
        try:
            # Verificar caché
            if self.config["cache_enabled"]:
                cached_data = await self._get_cache(key)
                if cached_data:
                    return cached_data["metadata"]

            # Obtener de base de conocimiento
            data = await self.memory.get_data(key)
            if data:
                return data["metadata"]

            return None

        except Exception as e:
            self.logger.error(f"Error obteniendo metadatos: {str(e)}")
            return None

    async def update_metadata(self, key: str, metadata: Dict[str, Any]):
        """
        Actualizar metadatos.

        Args:
            key: Clave de almacenamiento
            metadata: Nuevos metadatos
        """
        try:
            # Obtener datos actuales
            data = await self.retrieve(key, use_cache=False)
            if not data:
                raise ValueError(f"Datos no encontrados: {key}")

            # Actualizar metadatos
            storage_data = {
                "key": key,
                "data": data,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat(),
            }

            # Actualizar caché
            if self.config["cache_enabled"]:
                await self._store_cache(key, storage_data)

            # Actualizar base de conocimiento
            await self.memory.store_data(storage_data)

        except Exception as e:
            self.logger.error(f"Error actualizando metadatos: {str(e)}")
            raise

    async def _initialize_fs(self):
        """Inicializar sistema de archivos."""
        try:
            # Crear directorios necesarios
            paths = ["cache", "backups", "temp"]

            for path in paths:
                os.makedirs(path, exist_ok=True)

        except Exception as e:
            self.logger.error(f"Error inicializando sistema de archivos: {str(e)}")
            raise

    async def _maintenance_task(self):
        """Tarea de mantenimiento."""
        try:
            while self.active:
                # Limpiar caché
                await self._cleanup_cache()

                # Realizar backup si es necesario
                if self._should_backup():
                    await self._backup()

                # Esperar próximo ciclo
                await asyncio.sleep(3600)  # 1 hora

        except Exception as e:
            self.logger.error(f"Error en tarea de mantenimiento: {str(e)}")

    async def _load_cache(self):
        """Cargar caché desde disco."""
        try:
            cache_file = Path("cache/cache.json")
            if cache_file.exists():
                with open(cache_file, "r") as f:
                    cache_data = json.load(f)
                    self.cache = cache_data["data"]
                    self.cache_metadata = cache_data["metadata"]

        except Exception as e:
            self.logger.error(f"Error cargando caché: {str(e)}")

    async def _save_cache(self):
        """Guardar caché en disco."""
        try:
            cache_data = {"data": self.cache, "metadata": self.cache_metadata}

            with open("cache/cache.json", "w") as f:
                json.dump(cache_data, f)

        except Exception as e:
            self.logger.error(f"Error guardando caché: {str(e)}")

    async def _store_cache(self, key: str, data: Dict[str, Any]):
        """Almacenar en caché."""
        try:
            # Verificar tamaño de caché
            if self._get_cache_size() >= self.config["max_cache_size"]:
                await self._cleanup_cache()

            # Almacenar datos
            self.cache[key] = data

            # Actualizar metadatos
            self.cache_metadata[key] = CacheConfig(
                key=key,
                timestamp=datetime.now(),
                ttl=self.config["cache_ttl"],
                size=len(json.dumps(data)),
            )

        except Exception as e:
            self.logger.error(f"Error almacenando en caché: {str(e)}")
            raise

    async def _get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Obtener de caché."""
        try:
            # Verificar existencia
            if key not in self.cache:
                return None

            # Verificar TTL
            metadata = self.cache_metadata[key]
            if self._is_cache_expired(metadata):
                await self._delete_cache(key)
                return None

            return self.cache[key]

        except Exception as e:
            self.logger.error(f"Error obteniendo de caché: {str(e)}")
            return None

    async def _delete_cache(self, key: str):
        """Eliminar de caché."""
        try:
            if key in self.cache:
                del self.cache[key]

            if key in self.cache_metadata:
                del self.cache_metadata[key]

        except Exception as e:
            self.logger.error(f"Error eliminando de caché: {str(e)}")
            raise

    async def _cleanup_cache(self):
        """Limpiar caché."""
        try:
            # Eliminar entradas expiradas
            expired_keys = [
                key
                for key, metadata in self.cache_metadata.items()
                if self._is_cache_expired(metadata)
            ]

            for key in expired_keys:
                await self._delete_cache(key)

            # Eliminar entradas más antiguas si es necesario
            if self._get_cache_size() >= self.config["max_cache_size"]:
                sorted_keys = sorted(
                    self.cache_metadata.items(), key=lambda x: x[1].timestamp
                )

                for key, _ in sorted_keys:
                    await self._delete_cache(key)
                    if self._get_cache_size() < self.config["max_cache_size"]:
                        break

        except Exception as e:
            self.logger.error(f"Error limpiando caché: {str(e)}")

    def _is_cache_expired(self, metadata: CacheConfig) -> bool:
        """Verificar si entrada de caché expiró."""
        try:
            age = (datetime.now() - metadata.timestamp).total_seconds()
            return age >= metadata.ttl

        except Exception as e:
            self.logger.error(f"Error verificando expiración: {str(e)}")
            return True

    def _get_cache_size(self) -> int:
        """Obtener tamaño total de caché."""
        try:
            return sum(metadata.size for metadata in self.cache_metadata.values())

        except Exception as e:
            self.logger.error(f"Error calculando tamaño: {str(e)}")
            return 0

    def _should_backup(self) -> bool:
        """Verificar si se debe realizar backup."""
        try:
            if not self.last_backup:
                return True

            age = (datetime.now() - self.last_backup).total_seconds()
            return age >= self.config["backup_interval"]

        except Exception as e:
            self.logger.error(f"Error verificando backup: {str(e)}")
            return False

    async def _backup(self):
        """Realizar backup de datos."""
        try:
            # Crear directorio de backup
            backup_dir = Path(
                f"backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            os.makedirs(backup_dir, exist_ok=True)

            # Backup de caché
            cache_backup = {"data": self.cache, "metadata": self.cache_metadata}

            with open(backup_dir / "cache.json", "w") as f:
                json.dump(cache_backup, f)

            # Backup de base de conocimiento
            knowledge_backup = await self.memory.export_data()

            with open(backup_dir / "knowledge.json", "w") as f:
                json.dump(knowledge_backup, f)

            self.last_backup = datetime.now()
            self.logger.info(f"Backup realizado: {backup_dir}")

        except Exception as e:
            self.logger.error(f"Error realizando backup: {str(e)}")
            raise
