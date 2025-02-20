"""
Gestor de Sesiones para la Interfaz de Vendedor.

Este módulo implementa la lógica para manejar sesiones de vendedor,
garantizando la estabilidad y consistencia durante la elaboración de presupuestos.
"""
from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import UUID

from .models import SessionState, VendorSession

class SessionManager:
    """Administrador central de sesiones de vendedor."""
    
    def __init__(self, session_timeout: int = 30):
        """
        Inicializa el gestor de sesiones.
        
        Args:
            session_timeout: Tiempo en minutos antes de que una sesión expire
        """
        self._sessions: Dict[UUID, SessionState] = {}
        self._timeout = timedelta(minutes=session_timeout)
    
    def create_session(self, vendor_id: str, vendor_name: str) -> SessionState:
        """
        Crea una nueva sesión de vendedor.
        
        Args:
            vendor_id: ID único del vendedor
            vendor_name: Nombre del vendedor
        
        Returns:
            Nueva sesión inicializada
        """
        session = VendorSession(vendor_id=vendor_id, vendor_name=vendor_name)
        state = SessionState(session=session)
        self._sessions[session.id] = state
        return state
    
    def get_session(self, session_id: UUID) -> Optional[SessionState]:
        """
        Recupera una sesión existente.
        
        Args:
            session_id: ID de la sesión a recuperar
        
        Returns:
            Sesión si existe y está activa, None en otro caso
        """
        state = self._sessions.get(session_id)
        if not state or not state.session.is_active:
            return None
            
        if datetime.now() - state.session.last_activity > self._timeout:
            state.session.close()
            return None
            
        return state
    
    def close_session(self, session_id: UUID) -> None:
        """
        Cierra una sesión explícitamente.
        
        Args:
            session_id: ID de la sesión a cerrar
        """
        if state := self._sessions.get(session_id):
            state.session.close()
    
    def cleanup_expired(self) -> None:
        """Limpia las sesiones expiradas."""
        now = datetime.now()
        expired = [
            sid for sid, state in self._sessions.items()
            if state.session.is_active and 
            now - state.session.last_activity > self._timeout
        ]
        for sid in expired:
            self.close_session(sid)
    
    def get_active_sessions(self) -> Dict[UUID, SessionState]:
        """
        Retorna todas las sesiones activas.
        
        Returns:
            Diccionario de sesiones activas
        """
        return {
            sid: state for sid, state in self._sessions.items()
            if state.session.is_active
        }
