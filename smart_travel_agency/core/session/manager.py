"""
Gestor avanzado de sesiones con protección de estabilidad.

Este módulo implementa:
1. Gestión de sesiones de venta
2. Protección de estabilidad de datos
3. Control de modificaciones
4. Registro de cambios
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from decimal import Decimal

from prometheus_client import Counter, Gauge

# Métricas
ACTIVE_SESSIONS = Gauge("active_sessions_total", "Number of currently active sessions")

SESSION_OPERATIONS = Counter(
    "session_operations_total", "Number of session operations", ["operation_type"]
)


@dataclass
class SessionState:
    """Estado de una sesión de venta."""

    vendor_id: str
    customer_id: str
    start_time: datetime
    packages: Dict[str, Any]
    modifications: List[Dict[str, Any]]
    locked_data: Dict[str, Any] = None
    status: str = "active"
    last_optimization_pass: int = 0


class SessionManager:
    """
    Gestor avanzado de sesiones con protección de estabilidad.
    """

    def __init__(self):
        """Inicializar gestor."""
        self.active_sessions: Dict[str, SessionState] = {}
        self.logger = logging.getLogger(__name__)

    async def create_session(self, vendor_id: str, customer_id: str) -> str:
        """
        Crear nueva sesión con aislamiento de datos.

        Args:
            vendor_id: ID del vendedor
            customer_id: ID del cliente

        Returns:
            ID de la sesión creada
        """
        session_id = f"session_{vendor_id}_{customer_id}_{datetime.now().timestamp()}"

        session = SessionState(
            vendor_id=vendor_id,
            customer_id=customer_id,
            start_time=datetime.now(),
            packages={},
            modifications=[],
            locked_data={},
        )

        self.active_sessions[session_id] = session
        ACTIVE_SESSIONS.inc()
        SESSION_OPERATIONS.labels(operation_type="create").inc()

        self.logger.info(f"Created session {session_id} for customer {customer_id}")
        return session_id

    async def lock_session_data(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Bloquear datos para mantener estabilidad durante la sesión.

        Args:
            session_id: ID de la sesión
            data: Datos a bloquear

        Returns:
            True si se bloquearon los datos correctamente
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        session.locked_data = data.copy()
        SESSION_OPERATIONS.labels(operation_type="lock_data").inc()

        self.logger.info(f"Locked data for session {session_id}")
        return True

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """Obtener sesión."""
        return self.active_sessions.get(session_id)

    async def update_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        optimization_pass: Optional[int] = None,
    ) -> bool:
        """
        Actualizar sesión manteniendo estabilidad.

        Args:
            session_id: ID de la sesión
            data: Datos a actualizar
            optimization_pass: Número de pasada de optimización
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        # Registrar modificación
        modification = {
            "timestamp": datetime.now(),
            "data": data.copy(),
            "optimization_pass": optimization_pass,
        }
        session.modifications.append(modification)

        # Actualizar datos no bloqueados
        for key, value in data.items():
            if key not in session.locked_data:
                if isinstance(value, (int, float)):
                    setattr(session, key, Decimal(str(value)))
                else:
                    setattr(session, key, value)

        if optimization_pass:
            session.last_optimization_pass = optimization_pass

        SESSION_OPERATIONS.labels(operation_type="update").inc()
        return True

    async def close_session(self, session_id: str) -> bool:
        """Cerrar sesión y liberar recursos."""
        session = await self.get_session(session_id)
        if not session:
            return False

        session.status = "closed"
        session.locked_data = None  # Liberar datos bloqueados

        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            ACTIVE_SESSIONS.dec()

        SESSION_OPERATIONS.labels(operation_type="close").inc()
        self.logger.info(f"Closed session {session_id}")
        return True


# Instancia global del gestor
session_manager = SessionManager()


async def get_session_manager() -> SessionManager:
    """Obtener instancia única del gestor."""
    return session_manager
