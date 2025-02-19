"""Gestor de presupuestos en sesión."""

from typing import Dict, Any, Optional
from datetime import datetime
import json

from .storage_manager import storage_manager
from ..schemas.travel import PaqueteOLA

class SessionBudgetManager:
    """Maneja presupuestos durante sesiones activas de venta."""
    
    def __init__(self):
        """Inicializar gestor."""
        self.active_sessions: Dict[str, Dict] = {}
    
    async def create_session(self, vendor_id: str, customer_id: str) -> str:
        """Crear una nueva sesión de presupuesto."""
        session_id = f"session_{vendor_id}_{customer_id}_{datetime.now().timestamp()}"
        
        session_data = {
            'vendor_id': vendor_id,
            'customer_id': customer_id,
            'start_time': datetime.now().isoformat(),
            'packages': {},
            'modifications': []
        }
        
        # Guardar en storage
        await storage_manager.save(session_id, session_data)
        
        # Mantener en memoria
        self.active_sessions[session_id] = session_data
        
        return session_id
    
    async def add_package(self, session_id: str, package: PaqueteOLA) -> bool:
        """Agregar un paquete a la sesión."""
        # Cargar sesión
        session_data = await storage_manager.load(session_id)
        if not session_data:
            raise ValueError("Sesión no encontrada")
        
        # Agregar paquete
        package_id = f"pkg_{len(session_data['packages']) + 1}"
        session_data['packages'][package_id] = {
            'data': package.dict(),
            'added_at': datetime.now().isoformat(),
            'modifications': []
        }
        
        # Guardar cambios
        await storage_manager.save(session_id, session_data)
        self.active_sessions[session_id] = session_data
        
        return True
    
    async def get_budget(self, session_id: str) -> Dict[str, Any]:
        """Obtener el presupuesto actual de la sesión."""
        session_data = await storage_manager.load(session_id)
        if not session_data:
            raise ValueError("Sesión no encontrada")
        return session_data
    
    async def add_modification(self, session_id: str, modification: Dict[str, Any]) -> bool:
        """Agregar una modificación al presupuesto."""
        session_data = await storage_manager.load(session_id)
        if not session_data:
            raise ValueError("Sesión no encontrada")
        
        # Agregar modificación
        session_data['modifications'].append({
            'data': modification,
            'timestamp': datetime.now().isoformat()
        })
        
        # Guardar cambios
        await storage_manager.save(session_id, session_data)
        self.active_sessions[session_id] = session_data
        
        return True
    
    async def close_session(self, session_id: str) -> bool:
        """Cerrar una sesión de presupuesto."""
        session_data = await storage_manager.load(session_id)
        if not session_data:
            raise ValueError("Sesión no encontrada")
        
        # Marcar como cerrada
        session_data['closed_at'] = datetime.now().isoformat()
        
        # Guardar cambios finales
        await storage_manager.save(session_id, session_data)
        
        # Eliminar de memoria
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        return True

# Instancia global y función para inyección de dependencias
budget_manager = SessionBudgetManager()

def get_budget_manager() -> SessionBudgetManager:
    """Obtener instancia del gestor de presupuestos."""
    return budget_manager
