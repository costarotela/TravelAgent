"""
Gestor de sesiones para el agente de viajes.
Maneja el estado y flujo de las interacciones.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..schemas import SessionState
from ..config import config
from .storage_manager import storage_manager

class SessionManager:
    """Gestor de sesiones."""
    
    def __init__(self):
        """Inicializar gestor."""
        self.active_sessions: Dict[str, SessionState] = {}
        self.logger = logging.getLogger(__name__)
    
    async def init(self):
        """Inicializar gestor."""
        await storage_manager.init()
    
    async def create_session(
        self,
        vendor_id: str,
        customer_id: str
    ) -> str:
        """Crear nueva sesión."""
        session_id = f"session_{vendor_id}_{customer_id}_{datetime.now().timestamp()}"
        
        session = SessionState(
            vendor_id=vendor_id,
            customer_id=customer_id,
            start_time=datetime.now(),
            packages={},
            modifications=[]
        )
        
        self.active_sessions[session_id] = session
        await storage_manager.save(f"sessions:{session_id}", session.__dict__)
        
        self.logger.info(f"Created session {session_id} for customer {customer_id}")
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """Obtener sesión."""
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        data = await storage_manager.load(f"sessions:{session_id}")
        if data:
            session = SessionState(**data)
            self.active_sessions[session_id] = session
            return session
        
        return None
    
    async def update_session(
        self,
        session_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """Actualizar sesión."""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        for key, value in data.items():
            setattr(session, key, value)
        
        await storage_manager.save(f"sessions:{session_id}", session.__dict__)
        return True
    
    async def close_session(self, session_id: str) -> bool:
        """Cerrar sesión."""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        session.status = "closed"
        await storage_manager.save(f"sessions:{session_id}", session.__dict__)
        
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        self.logger.info(f"Closed session {session_id}")
        return True

# Instancia global del gestor
session_manager = SessionManager()

async def get_session_manager():
    """Obtener instancia del gestor."""
    await session_manager.init()
    return session_manager
