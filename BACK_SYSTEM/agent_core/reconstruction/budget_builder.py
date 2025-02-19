"""
Constructor de presupuestos.

Este módulo maneja:
1. Reconstrucción de presupuestos
2. Aplicación de cambios
3. Validación de estados
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from pathlib import Path

from .version_manager import VersionManager
from .history_manager import HistoryManager

class BudgetBuilder:
    """Constructor de presupuestos."""
    
    def __init__(
        self,
        version_manager: VersionManager,
        history_manager: HistoryManager
    ):
        """Inicializar constructor."""
        self.logger = logging.getLogger(__name__)
        self.version_manager = version_manager
        self.history_manager = history_manager
        
    async def reconstruct_budget(
        self,
        session_id: str,
        target_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reconstruir presupuesto a una versión específica."""
        try:
            # Si no se especifica versión, usar la más reciente
            if not target_version:
                versions = await self.version_manager.get_session_versions(
                    session_id,
                    limit=1
                )
                if not versions:
                    raise ValueError("No hay versiones disponibles")
                    
                return versions[0]["budget_data"]
                
            # Obtener versión específica
            version = await self.version_manager.get_version(target_version)
            if not version:
                raise ValueError(f"Versión {target_version} no encontrada")
                
            return version["budget_data"]
            
        except Exception as e:
            self.logger.error(f"Error reconstruyendo presupuesto: {str(e)}")
            raise
            
    async def apply_changes(
        self,
        session_id: str,
        base_version: str,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aplicar cambios sobre una versión base."""
        try:
            # Obtener versión base
            budget = await self.reconstruct_budget(
                session_id,
                target_version=base_version
            )
            
            # Aplicar cada cambio en orden
            for change in changes:
                if change["change_type"] == "add_package":
                    budget["packages"].append(change["details"]["package"])
                    
                elif change["change_type"] == "remove_package":
                    pkg_id = change["details"]["package_id"]
                    budget["packages"] = [
                        p for p in budget["packages"]
                        if p["id"] != pkg_id
                    ]
                    
                elif change["change_type"] == "modify_package":
                    pkg_id = change["details"]["package_id"]
                    for i, pkg in enumerate(budget["packages"]):
                        if pkg["id"] == pkg_id:
                            budget["packages"][i].update(
                                change["details"]["modifications"]
                            )
                            break
                            
                elif change["change_type"] == "update_metadata":
                    budget["metadata"].update(change["details"])
                    
            return budget
            
        except Exception as e:
            self.logger.error(f"Error aplicando cambios: {str(e)}")
            raise
            
    async def validate_state(
        self,
        session_id: str,
        budget_data: Dict[str, Any]
    ) -> bool:
        """Validar estado del presupuesto."""
        try:
            # Validaciones básicas
            if not isinstance(budget_data, dict):
                return False
                
            required_keys = ["packages", "metadata"]
            if not all(k in budget_data for k in required_keys):
                return False
                
            if not isinstance(budget_data["packages"], list):
                return False
                
            # Validar paquetes
            for package in budget_data["packages"]:
                if not isinstance(package, dict):
                    return False
                    
                required_pkg_keys = ["id", "name", "price"]
                if not all(k in package for k in required_pkg_keys):
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error validando estado: {str(e)}")
            return False
            
    async def create_checkpoint(
        self,
        session_id: str,
        budget_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Crear punto de control del presupuesto."""
        try:
            # Validar estado
            if not await self.validate_state(session_id, budget_data):
                raise ValueError("Estado inválido del presupuesto")
                
            # Crear nueva versión
            return await self.version_manager.create_version(
                session_id,
                budget_data,
                metadata
            )
            
        except Exception as e:
            self.logger.error(f"Error creando checkpoint: {str(e)}")
            raise
