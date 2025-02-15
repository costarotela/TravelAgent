"""
Gestor de sesiones para el agente de viajes.
Maneja el estado y flujo de las interacciones.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import asyncio
from uuid import uuid4
import json

from ..schemas import (
    SalesQuery,
    CustomerProfile,
    SearchCriteria,
    TravelPackage,
    SessionState,
    SalesReport
)
from ..config import config
from .cache_manager import cache_manager
from .storage_manager import storage_manager

class SessionManager:
    """
    Gestor avanzado de sesiones de venta.
    
    Características:
    1. Gestión de estado de sesión
    2. Persistencia y recuperación
    3. Limpieza automática
    4. Métricas y análisis
    5. Manejo de concurrencia
    """
    
    def __init__(self):
        """Inicializar gestor de sesiones."""
        self.logger = logging.getLogger(__name__)
        
        # Configuración
        self.session_ttl = config.get("session_ttl", 3600)  # 1 hora
        self.cleanup_interval = config.get("session_cleanup_interval", 300)  # 5 minutos
        self.max_sessions = config.get("max_concurrent_sessions", 100)
        
        # Estado interno
        self.active_sessions: Dict[str, SessionState] = {}
        self.session_locks: Dict[str, asyncio.Lock] = {}
        
        # Métricas
        self.metrics = {
            "sessions_created": 0,
            "sessions_completed": 0,
            "sessions_expired": 0,
            "total_interaction_time": 0,
            "conversion_rate": 0.0
        }
        
        # Iniciar limpieza automática
        asyncio.create_task(self._cleanup_loop())
    
    async def create_session(
        self,
        query: SalesQuery,
        customer: CustomerProfile
    ) -> SessionState:
        """
        Crear nueva sesión de venta.
        
        Args:
            query: Consulta inicial
            customer: Perfil del cliente
        
        Returns:
            Estado inicial de la sesión
        """
        # Verificar límite de sesiones
        if len(self.active_sessions) >= self.max_sessions:
            raise RuntimeError("Maximum number of concurrent sessions reached")
        
        session_id = str(uuid4())
        now = datetime.utcnow()
        
        # Crear estado inicial
        state = SessionState(
            session_id=session_id,
            query=query,
            current_analysis={},
            current_budget=None,
            interaction_count=0,
            start_time=now,
            last_update=now
        )
        
        # Guardar estado
        self.active_sessions[session_id] = state
        self.session_locks[session_id] = asyncio.Lock()
        
        # Persistir en almacenamiento
        await storage_manager.save(
            "sessions",
            {
                "session_id": session_id,
                "customer_id": customer.id,
                "state": state.__dict__,
                "created_at": now.isoformat()
            }
        )
        
        # Actualizar métricas
        self.metrics["sessions_created"] += 1
        
        self.logger.info(f"Created session {session_id} for customer {customer.id}")
        return state
    
    async def get_session(
        self,
        session_id: str
    ) -> Optional[SessionState]:
        """
        Obtener estado de sesión.
        
        Args:
            session_id: ID de la sesión
        
        Returns:
            Estado actual o None si no existe
        """
        # Intentar obtener de memoria
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # Intentar recuperar de almacenamiento
        stored = await storage_manager.get("sessions", session_id)
        if stored:
            state = SessionState(**stored["state"])
            self.active_sessions[session_id] = state
            self.session_locks[session_id] = asyncio.Lock()
            return state
        
        return None
    
    async def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> Optional[SessionState]:
        """
        Actualizar estado de sesión.
        
        Args:
            session_id: ID de la sesión
            updates: Cambios a aplicar
        
        Returns:
            Estado actualizado o None si no existe
        """
        if session_id not in self.active_sessions:
            return None
        
        async with self.session_locks[session_id]:
            state = self.active_sessions[session_id]
            
            # Aplicar actualizaciones
            for key, value in updates.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            
            # Actualizar timestamp
            state.last_update = datetime.utcnow()
            state.interaction_count += 1
            
            # Persistir cambios
            await storage_manager.update(
                "sessions",
                session_id,
                {"state": state.__dict__}
            )
            
            return state
    
    async def end_session(
        self,
        session_id: str,
        outcome: Dict[str, Any]
    ) -> Optional[SalesReport]:
        """
        Finalizar sesión de venta.
        
        Args:
            session_id: ID de la sesión
            outcome: Resultado final
        
        Returns:
            Reporte de la sesión o None si no existe
        """
        if session_id not in self.active_sessions:
            return None
        
        async with self.session_locks[session_id]:
            state = self.active_sessions[session_id]
            
            # Generar reporte
            duration = (datetime.utcnow() - state.start_time).total_seconds()
            report = SalesReport(
                query=state.query,
                final_budget=state.current_budget,
                interaction_count=state.interaction_count,
                end_reason=outcome.get("reason", "completed"),
                insights=outcome.get("insights", {}),
                metrics=outcome.get("metrics", {}),
                duration=int(duration),
                conversion=outcome.get("conversion", False),
                feedback_summary=outcome.get("feedback", None),
                recommendations=outcome.get("recommendations", [])
            )
            
            # Persistir reporte
            await storage_manager.save(
                "sales_reports",
                report.__dict__
            )
            
            # Limpiar sesión
            del self.active_sessions[session_id]
            del self.session_locks[session_id]
            
            # Actualizar métricas
            self.metrics["sessions_completed"] += 1
            self.metrics["total_interaction_time"] += duration
            if report.conversion:
                self._update_conversion_rate(True)
            
            self.logger.info(
                f"Ended session {session_id} - "
                f"Duration: {duration}s, "
                f"Interactions: {state.interaction_count}, "
                f"Conversion: {report.conversion}"
            )
            
            return report
    
    async def get_active_sessions(
        self,
        customer_id: Optional[str] = None
    ) -> List[SessionState]:
        """
        Obtener sesiones activas.
        
        Args:
            customer_id: Filtrar por cliente
        
        Returns:
            Lista de sesiones activas
        """
        if customer_id:
            query = {"customer_id": customer_id}
            stored = await storage_manager.find("sessions", query)
            return [
                self.active_sessions.get(s["session_id"]) or SessionState(**s["state"])
                for s in stored
                if s["session_id"] in self.active_sessions
            ]
        
        return list(self.active_sessions.values())
    
    async def _cleanup_loop(self):
        """Loop de limpieza automática."""
        while True:
            try:
                await self._cleanup_expired_sessions()
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                self.logger.error(f"Session cleanup error: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Limpiar sesiones expiradas."""
        now = datetime.utcnow()
        expired = []
        
        for session_id, state in self.active_sessions.items():
            if (now - state.last_update).total_seconds() > self.session_ttl:
                expired.append(session_id)
        
        for session_id in expired:
            async with self.session_locks[session_id]:
                # Generar reporte de sesión expirada
                await self.end_session(
                    session_id,
                    {
                        "reason": "expired",
                        "conversion": False
                    }
                )
                
                self.metrics["sessions_expired"] += 1
    
    def _update_conversion_rate(self, conversion: bool):
        """Actualizar tasa de conversión."""
        total = self.metrics["sessions_completed"]
        conversions = self.metrics["conversion_rate"] * (total - 1)
        
        if conversion:
            conversions += 1
        
        self.metrics["conversion_rate"] = conversions / total if total > 0 else 0
    
    def get_metrics(self) -> Dict[str, Union[int, float]]:
        """
        Obtener métricas de sesiones.
        
        Returns:
            Dict con métricas
        """
        avg_duration = (
            self.metrics["total_interaction_time"] /
            self.metrics["sessions_completed"]
            if self.metrics["sessions_completed"] > 0
            else 0
        )
        
        return {
            **self.metrics,
            "active_sessions": len(self.active_sessions),
            "average_duration": avg_duration
        }

# Instancia global
session_manager = SessionManager()
