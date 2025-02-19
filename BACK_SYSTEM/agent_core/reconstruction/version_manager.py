"""
Gestor de versiones de presupuestos.

Este módulo maneja:
1. Control de versiones de presupuestos
2. Almacenamiento de estados
3. Comparación de versiones
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import logging
from pathlib import Path

class VersionManager:
    """Gestor de versiones de presupuestos."""
    
    def __init__(self, storage_path: Path):
        """Inicializar gestor de versiones."""
        self.logger = logging.getLogger(__name__)
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    async def create_version(
        self,
        session_id: str,
        budget_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Crear nueva versión del presupuesto."""
        try:
            # Crear identificador de versión
            timestamp = datetime.now().isoformat()
            version_id = f"{session_id}_{timestamp}"
            
            # Preparar datos
            version_data = {
                "version_id": version_id,
                "session_id": session_id,
                "timestamp": timestamp,
                "budget_data": budget_data,
                "metadata": metadata or {}
            }
            
            # Guardar versión
            version_path = self.storage_path / f"{version_id}.json"
            with open(version_path, "w") as f:
                json.dump(version_data, f, indent=2)
                
            self.logger.info(f"Creada versión {version_id} para sesión {session_id}")
            return version_id
            
        except Exception as e:
            self.logger.error(f"Error creando versión: {str(e)}")
            raise
            
    async def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        """Obtener versión específica."""
        try:
            version_path = self.storage_path / f"{version_id}.json"
            if not version_path.exists():
                return None
                
            with open(version_path, "r") as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"Error obteniendo versión {version_id}: {str(e)}")
            return None
            
    async def get_session_versions(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Obtener todas las versiones de una sesión."""
        try:
            # Buscar archivos de versión
            version_files = sorted(
                self.storage_path.glob(f"{session_id}_*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            # Limitar cantidad si es necesario
            if limit:
                version_files = version_files[:limit]
                
            # Cargar datos
            versions = []
            for vf in version_files:
                with open(vf, "r") as f:
                    versions.append(json.load(f))
                    
            return versions
            
        except Exception as e:
            self.logger.error(
                f"Error obteniendo versiones de sesión {session_id}: {str(e)}"
            )
            return []
            
    async def compare_versions(
        self,
        version_id_1: str,
        version_id_2: str
    ) -> Dict[str, Any]:
        """Comparar dos versiones de presupuesto."""
        try:
            # Obtener versiones
            v1 = await self.get_version(version_id_1)
            v2 = await self.get_version(version_id_2)
            
            if not v1 or not v2:
                raise ValueError("Versión no encontrada")
                
            # Comparar datos
            changes = {
                "packages_added": [],
                "packages_removed": [],
                "packages_modified": [],
                "metadata_changes": {}
            }
            
            # Comparar paquetes
            v1_pkgs = {p["id"]: p for p in v1["budget_data"]["packages"]}
            v2_pkgs = {p["id"]: p for p in v2["budget_data"]["packages"]}
            
            # Paquetes agregados
            for pkg_id in set(v2_pkgs.keys()) - set(v1_pkgs.keys()):
                changes["packages_added"].append(v2_pkgs[pkg_id])
                
            # Paquetes eliminados
            for pkg_id in set(v1_pkgs.keys()) - set(v2_pkgs.keys()):
                changes["packages_removed"].append(v1_pkgs[pkg_id])
                
            # Paquetes modificados
            for pkg_id in set(v1_pkgs.keys()) & set(v2_pkgs.keys()):
                if v1_pkgs[pkg_id] != v2_pkgs[pkg_id]:
                    changes["packages_modified"].append({
                        "before": v1_pkgs[pkg_id],
                        "after": v2_pkgs[pkg_id]
                    })
                    
            # Comparar metadata
            for key in set(v2["metadata"].keys()) | set(v1["metadata"].keys()):
                if v1["metadata"].get(key) != v2["metadata"].get(key):
                    changes["metadata_changes"][key] = {
                        "before": v1["metadata"].get(key),
                        "after": v2["metadata"].get(key)
                    }
                    
            return changes
            
        except Exception as e:
            self.logger.error(f"Error comparando versiones: {str(e)}")
            raise
            
    async def delete_version(self, version_id: str) -> bool:
        """Eliminar una versión específica."""
        try:
            version_path = self.storage_path / f"{version_id}.json"
            if version_path.exists():
                version_path.unlink()
                self.logger.info(f"Eliminada versión {version_id}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error eliminando versión {version_id}: {str(e)}")
            return False
