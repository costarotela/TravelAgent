"""
Gestor de historial de cambios.

Este módulo maneja:
1. Registro de cambios
2. Historial de modificaciones
3. Trazabilidad de cambios
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from pathlib import Path
import json

class HistoryManager:
    """Gestor de historial de cambios."""
    
    def __init__(self, storage_path: Path):
        """Inicializar gestor de historial."""
        self.logger = logging.getLogger(__name__)
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    async def record_change(
        self,
        session_id: str,
        change_type: str,
        details: Dict[str, Any],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Registrar un cambio en el historial."""
        try:
            # Crear identificador de cambio
            timestamp = datetime.now().isoformat()
            change_id = f"{session_id}_{timestamp}"
            
            # Preparar datos
            change_data = {
                "change_id": change_id,
                "session_id": session_id,
                "timestamp": timestamp,
                "change_type": change_type,
                "details": details,
                "user_id": user_id,
                "metadata": metadata or {}
            }
            
            # Guardar cambio
            change_path = self.storage_path / f"{change_id}.json"
            with open(change_path, "w") as f:
                json.dump(change_data, f, indent=2)
                
            self.logger.info(
                f"Registrado cambio {change_id} tipo {change_type} "
                f"para sesión {session_id}"
            )
            return change_id
            
        except Exception as e:
            self.logger.error(f"Error registrando cambio: {str(e)}")
            raise
            
    async def get_session_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
        change_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Obtener historial de cambios de una sesión."""
        try:
            # Buscar archivos de cambios
            change_files = sorted(
                self.storage_path.glob(f"{session_id}_*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            # Cargar y filtrar cambios
            changes = []
            for cf in change_files:
                with open(cf, "r") as f:
                    change = json.load(f)
                    if not change_type or change["change_type"] == change_type:
                        changes.append(change)
                        
                        if limit and len(changes) >= limit:
                            break
                            
            return changes
            
        except Exception as e:
            self.logger.error(
                f"Error obteniendo historial de sesión {session_id}: {str(e)}"
            )
            return []
            
    async def get_change(self, change_id: str) -> Optional[Dict[str, Any]]:
        """Obtener detalles de un cambio específico."""
        try:
            change_path = self.storage_path / f"{change_id}.json"
            if not change_path.exists():
                return None
                
            with open(change_path, "r") as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"Error obteniendo cambio {change_id}: {str(e)}")
            return None
            
    async def get_user_changes(
        self,
        user_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Obtener cambios realizados por un usuario."""
        try:
            # Buscar todos los archivos de cambios
            all_changes = []
            for change_file in self.storage_path.glob("*.json"):
                with open(change_file, "r") as f:
                    change = json.load(f)
                    if change["user_id"] == user_id:
                        all_changes.append(change)
                        
                        if limit and len(all_changes) >= limit:
                            break
                            
            # Ordenar por timestamp
            return sorted(
                all_changes,
                key=lambda x: x["timestamp"],
                reverse=True
            )
            
        except Exception as e:
            self.logger.error(
                f"Error obteniendo cambios de usuario {user_id}: {str(e)}"
            )
            return []
