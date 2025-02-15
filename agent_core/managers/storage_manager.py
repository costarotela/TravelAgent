"""
Gestor de almacenamiento con soporte para múltiples backends.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod
import asyncio
import aiofiles
import aiosqlite
import motor.motor_asyncio
from bson import ObjectId
from ..config import config

class StorageBackend(ABC):
    """Interfaz base para backends de almacenamiento."""
    
    @abstractmethod
    async def save(
        self,
        collection: str,
        data: Dict[str, Any]
    ) -> str:
        """Guardar documento."""
        pass
    
    @abstractmethod
    async def get(
        self,
        collection: str,
        id: str
    ) -> Optional[Dict[str, Any]]:
        """Obtener documento."""
        pass
    
    @abstractmethod
    async def update(
        self,
        collection: str,
        id: str,
        data: Dict[str, Any]
    ) -> bool:
        """Actualizar documento."""
        pass
    
    @abstractmethod
    async def delete(
        self,
        collection: str,
        id: str
    ) -> bool:
        """Eliminar documento."""
        pass
    
    @abstractmethod
    async def find(
        self,
        collection: str,
        query: Dict[str, Any],
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Buscar documentos."""
        pass

class MongoBackend(StorageBackend):
    """Backend de almacenamiento usando MongoDB."""
    
    def __init__(self, mongo_config: Dict[str, Any]):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(
            f"mongodb://{mongo_config['host']}:{mongo_config['port']}"
        )
        self.db = self.client[mongo_config['name']]
    
    async def save(
        self,
        collection: str,
        data: Dict[str, Any]
    ) -> str:
        """Guardar documento en MongoDB."""
        result = await self.db[collection].insert_one(data)
        return str(result.inserted_id)
    
    async def get(
        self,
        collection: str,
        id: str
    ) -> Optional[Dict[str, Any]]:
        """Obtener documento de MongoDB."""
        doc = await self.db[collection].find_one({"_id": ObjectId(id)})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc
    
    async def update(
        self,
        collection: str,
        id: str,
        data: Dict[str, Any]
    ) -> bool:
        """Actualizar documento en MongoDB."""
        result = await self.db[collection].update_one(
            {"_id": ObjectId(id)},
            {"$set": data}
        )
        return result.modified_count > 0
    
    async def delete(
        self,
        collection: str,
        id: str
    ) -> bool:
        """Eliminar documento de MongoDB."""
        result = await self.db[collection].delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0
    
    async def find(
        self,
        collection: str,
        query: Dict[str, Any],
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Buscar documentos en MongoDB."""
        cursor = self.db[collection].find(query)
        if limit:
            cursor = cursor.limit(limit)
        
        docs = await cursor.to_list(length=None)
        for doc in docs:
            doc["_id"] = str(doc["_id"])
        return docs

class SQLiteBackend(StorageBackend):
    """Backend de almacenamiento usando SQLite."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        asyncio.create_task(self._init_db())
    
    async def _init_db(self):
        """Inicializar base de datos SQLite."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
    
    async def save(
        self,
        collection: str,
        data: Dict[str, Any]
    ) -> str:
        """Guardar documento en SQLite."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO documents (collection, data) VALUES (?, ?)",
                (collection, json.dumps(data))
            )
            await db.commit()
            return str(cursor.lastrowid)
    
    async def get(
        self,
        collection: str,
        id: str
    ) -> Optional[Dict[str, Any]]:
        """Obtener documento de SQLite."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT data FROM documents WHERE id = ? AND collection = ?",
                (int(id), collection)
            )
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])
        return None
    
    async def update(
        self,
        collection: str,
        id: str,
        data: Dict[str, Any]
    ) -> bool:
        """Actualizar documento en SQLite."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                UPDATE documents 
                SET data = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND collection = ?
                """,
                (json.dumps(data), int(id), collection)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def delete(
        self,
        collection: str,
        id: str
    ) -> bool:
        """Eliminar documento de SQLite."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM documents WHERE id = ? AND collection = ?",
                (int(id), collection)
            )
            await db.commit()
            return cursor.rowcount > 0
    
    async def find(
        self,
        collection: str,
        query: Dict[str, Any],
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Buscar documentos en SQLite."""
        conditions = []
        params = []
        for key, value in query.items():
            conditions.append(f"json_extract(data, '$.{key}') = ?")
            params.append(value)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        limit_clause = f" LIMIT {limit}" if limit else ""
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"""
                SELECT id, data 
                FROM documents 
                WHERE collection = ? AND {where_clause}
                {limit_clause}
                """,
                (collection, *params)
            )
            rows = await cursor.fetchall()
            return [
                {"_id": str(row[0]), **json.loads(row[1])}
                for row in rows
            ]

class FileBackend(StorageBackend):
    """Backend de almacenamiento usando sistema de archivos."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_collection_path(self, collection: str) -> Path:
        """Obtener ruta de colección."""
        path = self.base_path / collection
        path.mkdir(exist_ok=True)
        return path
    
    async def save(
        self,
        collection: str,
        data: Dict[str, Any]
    ) -> str:
        """Guardar documento en archivo."""
        collection_path = self._get_collection_path(collection)
        id = str(ObjectId())
        file_path = collection_path / f"{id}.json"
        
        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(data, indent=2))
        
        return id
    
    async def get(
        self,
        collection: str,
        id: str
    ) -> Optional[Dict[str, Any]]:
        """Obtener documento de archivo."""
        collection_path = self._get_collection_path(collection)
        file_path = collection_path / f"{id}.json"
        
        if not file_path.exists():
            return None
        
        async with aiofiles.open(file_path, "r") as f:
            content = await f.read()
            return json.loads(content)
    
    async def update(
        self,
        collection: str,
        id: str,
        data: Dict[str, Any]
    ) -> bool:
        """Actualizar documento en archivo."""
        collection_path = self._get_collection_path(collection)
        file_path = collection_path / f"{id}.json"
        
        if not file_path.exists():
            return False
        
        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(data, indent=2))
        
        return True
    
    async def delete(
        self,
        collection: str,
        id: str
    ) -> bool:
        """Eliminar documento de archivo."""
        collection_path = self._get_collection_path(collection)
        file_path = collection_path / f"{id}.json"
        
        if not file_path.exists():
            return False
        
        file_path.unlink()
        return True
    
    async def find(
        self,
        collection: str,
        query: Dict[str, Any],
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Buscar documentos en archivos."""
        collection_path = self._get_collection_path(collection)
        results = []
        
        for file_path in collection_path.glob("*.json"):
            if limit and len(results) >= limit:
                break
            
            async with aiofiles.open(file_path, "r") as f:
                content = await f.read()
                data = json.loads(content)
                
                # Verificar si cumple con la query
                matches = True
                for key, value in query.items():
                    if key not in data or data[key] != value:
                        matches = False
                        break
                
                if matches:
                    results.append({
                        "_id": file_path.stem,
                        **data
                    })
        
        return results

class StorageManager:
    """
    Gestor de almacenamiento avanzado.
    
    Características:
    1. Múltiples backends (MongoDB, SQLite, Archivos)
    2. Operaciones asíncronas
    3. Búsqueda y consultas
    4. Validación de datos
    5. Métricas y monitoreo
    """
    
    def __init__(self):
        """Inicializar gestor de almacenamiento."""
        self.logger = logging.getLogger(__name__)
        
        # Configurar backends
        self.backends: Dict[str, StorageBackend] = {}
        self._setup_backends()
        
        # Métricas
        self.operations = {
            "save": 0,
            "get": 0,
            "update": 0,
            "delete": 0,
            "find": 0
        }
    
    def _setup_backends(self) -> None:
        """Configurar backends de almacenamiento."""
        db_config = config.db.__dict__
        
        # MongoDB si está configurado
        if db_config.get("type") == "mongodb":
            try:
                self.backends["mongodb"] = MongoBackend(db_config)
                self.logger.info("MongoDB backend initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize MongoDB: {e}")
        
        # SQLite como alternativa
        data_dir = config.base_path / "data"
        data_dir.mkdir(exist_ok=True)
        sqlite_path = str(data_dir / "storage.db")
        self.backends["sqlite"] = SQLiteBackend(sqlite_path)
        
        # Sistema de archivos como fallback
        files_path = str(data_dir / "files")
        self.backends["files"] = FileBackend(files_path)
    
    def _get_backend(self, collection: str) -> StorageBackend:
        """Seleccionar backend apropiado."""
        if "mongodb" in self.backends:
            return self.backends["mongodb"]
        if collection.startswith("large_"):
            return self.backends["files"]
        return self.backends["sqlite"]
    
    async def save(
        self,
        collection: str,
        data: Dict[str, Any]
    ) -> str:
        """
        Guardar documento.
        
        Args:
            collection: Nombre de la colección
            data: Datos a guardar
        
        Returns:
            ID del documento guardado
        """
        backend = self._get_backend(collection)
        
        try:
            # Agregar metadatos
            data["created_at"] = datetime.utcnow().isoformat()
            data["updated_at"] = data["created_at"]
            
            id = await backend.save(collection, data)
            self.operations["save"] += 1
            return id
            
        except Exception as e:
            self.logger.error(f"Storage save error: {e}")
            raise
    
    async def get(
        self,
        collection: str,
        id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener documento.
        
        Args:
            collection: Nombre de la colección
            id: ID del documento
        
        Returns:
            Documento o None si no existe
        """
        backend = self._get_backend(collection)
        
        try:
            doc = await backend.get(collection, id)
            self.operations["get"] += 1
            return doc
            
        except Exception as e:
            self.logger.error(f"Storage get error: {e}")
            return None
    
    async def update(
        self,
        collection: str,
        id: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Actualizar documento.
        
        Args:
            collection: Nombre de la colección
            id: ID del documento
            data: Nuevos datos
        
        Returns:
            True si se actualizó, False si no
        """
        backend = self._get_backend(collection)
        
        try:
            # Actualizar metadatos
            data["updated_at"] = datetime.utcnow().isoformat()
            
            success = await backend.update(collection, id, data)
            self.operations["update"] += 1
            return success
            
        except Exception as e:
            self.logger.error(f"Storage update error: {e}")
            return False
    
    async def delete(
        self,
        collection: str,
        id: str
    ) -> bool:
        """
        Eliminar documento.
        
        Args:
            collection: Nombre de la colección
            id: ID del documento
        
        Returns:
            True si se eliminó, False si no
        """
        backend = self._get_backend(collection)
        
        try:
            success = await backend.delete(collection, id)
            self.operations["delete"] += 1
            return success
            
        except Exception as e:
            self.logger.error(f"Storage delete error: {e}")
            return False
    
    async def find(
        self,
        collection: str,
        query: Dict[str, Any],
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Buscar documentos.
        
        Args:
            collection: Nombre de la colección
            query: Criterios de búsqueda
            limit: Límite de resultados
        
        Returns:
            Lista de documentos que coinciden
        """
        backend = self._get_backend(collection)
        
        try:
            docs = await backend.find(collection, query, limit)
            self.operations["find"] += 1
            return docs
            
        except Exception as e:
            self.logger.error(f"Storage find error: {e}")
            return []
    
    def get_metrics(self) -> Dict[str, Union[int, Dict[str, int]]]:
        """
        Obtener métricas de almacenamiento.
        
        Returns:
            Dict con métricas
        """
        return {
            "backends": list(self.backends.keys()),
            "operations": self.operations,
            "total_operations": sum(self.operations.values())
        }

# Instancia global
storage_manager = StorageManager()
