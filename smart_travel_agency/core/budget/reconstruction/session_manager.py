"""
Gestión de sesiones de venta.

Este módulo implementa:
1. Control de sesiones activas
2. Estabilidad durante la venta
3. Aislamiento de datos
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

@dataclass
class SessionState:
    """Estado de una sesión de venta."""
    budget_id: str
    seller_id: str
    start_time: datetime
    last_activity: datetime
    is_active: bool = True
    locked_data: Dict[str, Any] = None
    modifications: List[Dict[str, Any]] = None

class SessionManager:
    """
    Gestor de sesiones de venta.
    
    Responsabilidades:
    1. Control de sesiones activas
    2. Aislamiento de datos durante venta
    3. Registro de modificaciones
    """

    def __init__(self):
        """Inicializar manager."""
        self.logger = logging.getLogger(__name__)
        self._active_sessions: Dict[str, SessionState] = {}
        self._session_timeout = timedelta(minutes=30)

    async def start_session(
        self,
        budget_id: str,
        seller_id: str
    ) -> SessionState:
        """
        Iniciar sesión de venta.
        
        Args:
            budget_id: ID del presupuesto
            seller_id: ID del vendedor
        """
        # Verificar si ya existe sesión
        if budget_id in self._active_sessions:
            session = self._active_sessions[budget_id]
            if session.is_active:
                if session.seller_id != seller_id:
                    raise ValueError(
                        f"Presupuesto {budget_id} ya tiene sesión activa "
                        f"con vendedor {session.seller_id}"
                    )
                return session

        # Crear nueva sesión
        now = datetime.now()
        session = SessionState(
            budget_id=budget_id,
            seller_id=seller_id,
            start_time=now,
            last_activity=now,
            locked_data={},
            modifications=[]
        )
        self._active_sessions[budget_id] = session
        return session

    async def end_session(
        self,
        budget_id: str,
        seller_id: str
    ) -> None:
        """
        Finalizar sesión de venta.
        
        Args:
            budget_id: ID del presupuesto
            seller_id: ID del vendedor
        """
        if budget_id not in self._active_sessions:
            return

        session = self._active_sessions[budget_id]
        if session.seller_id != seller_id:
            raise ValueError(
                f"Sesión pertenece a vendedor {session.seller_id}, "
                f"no a {seller_id}"
            )

        session.is_active = False
        session.last_activity = datetime.now()

    async def get_active_session(
        self,
        budget_id: str
    ) -> Optional[SessionState]:
        """
        Obtener sesión activa.
        
        Args:
            budget_id: ID del presupuesto
        """
        if budget_id not in self._active_sessions:
            return None

        session = self._active_sessions[budget_id]
        if not session.is_active:
            return None

        # Verificar timeout
        if (datetime.now() - session.last_activity) > self._session_timeout:
            session.is_active = False
            return None

        return session

    async def update_session_data(
        self,
        budget_id: str,
        seller_id: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Actualizar datos de sesión.
        
        Args:
            budget_id: ID del presupuesto
            seller_id: ID del vendedor
            data: Datos a actualizar
        """
        session = await self.get_active_session(budget_id)
        if not session:
            raise ValueError(f"No hay sesión activa para {budget_id}")

        if session.seller_id != seller_id:
            raise ValueError(
                f"Sesión pertenece a vendedor {session.seller_id}, "
                f"no a {seller_id}"
            )

        # Registrar modificación
        session.modifications.append({
            "timestamp": datetime.now(),
            "data": data
        })

        # Actualizar datos
        session.locked_data.update(data)
        session.last_activity = datetime.now()

    async def get_session_data(
        self,
        budget_id: str
    ) -> Dict[str, Any]:
        """
        Obtener datos de sesión.
        
        Args:
            budget_id: ID del presupuesto
        """
        session = await self.get_active_session(budget_id)
        if not session:
            return {}
        return session.locked_data

# Instancia global
_manager: Optional[SessionManager] = None

def get_session_manager() -> SessionManager:
    """Obtener instancia del manager."""
    global _manager
    if not _manager:
        _manager = SessionManager()
    return _manager
