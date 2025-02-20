"""Gestor de almacenamiento con SQLite."""

import json
import aiosqlite
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..config import config


class StorageManager:
    """Gestor de almacenamiento."""

    def __init__(self):
        """Inicializar gestor."""
        self.conn = None
        self.db_path = None

    async def init(self):
        """Inicializar base de datos."""
        self.db_path = config.data_dir / "storage.db"
        self.conn = await aiosqlite.connect(self.db_path)

        # Crear tabla si no existe
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS storage (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        await self.conn.commit()

    async def close(self):
        """Cerrar conexión."""
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def save(self, key: str, data: Dict[str, Any]) -> bool:
        """Guardar datos."""
        if not self.conn:
            await self.init()

        try:
            await self.conn.execute(
                """
                INSERT OR REPLACE INTO storage (key, data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (key, json.dumps(data)),
            )
            await self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False

    async def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Cargar datos."""
        if not self.conn:
            await self.init()

        try:
            async with self.conn.execute(
                "SELECT data FROM storage WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception as e:
            print(f"Error loading data: {e}")
        return None

    async def delete(self, key: str) -> bool:
        """Eliminar datos."""
        if not self.conn:
            await self.init()

        try:
            await self.conn.execute("DELETE FROM storage WHERE key = ?", (key,))
            await self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting data: {e}")
            return False

    async def list(self, prefix: str = "") -> List[str]:
        """Listar claves."""
        if not self.conn:
            await self.init()

        try:
            async with self.conn.execute(
                "SELECT key FROM storage WHERE key LIKE ?", (f"{prefix}%",)
            ) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            print(f"Error listing keys: {e}")
            return []


# Instancia global del gestor
storage_manager = StorageManager()
