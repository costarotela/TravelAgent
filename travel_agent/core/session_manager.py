"""
Administrador de sesiones de venta.

Este módulo se encarga de:
1. Gestionar sesiones de venta
2. Mantener estado de búsquedas
3. Coordinar componentes
4. Gestionar interacciones
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import asyncio
from uuid import uuid4

from .schemas import SearchCriteria, TravelPackage, Budget
from .package_analyzer import PackageAnalyzer
from .price_monitor import PriceMonitor
from .opportunity_tracker import OpportunityTracker
from .recommendation_engine import RecommendationEngine
from ..memory.supabase import SupabaseMemory


class SessionManager:
    """Administrador de sesiones de venta."""

    def __init__(self):
        """Inicializar administrador."""
        self.logger = logging.getLogger(__name__)
        self.memory = SupabaseMemory()

        # Componentes core
        self.analyzer = PackageAnalyzer()
        self.price_monitor = PriceMonitor()
        self.opportunity_tracker = OpportunityTracker()
        self.recommendation_engine = RecommendationEngine()

        # Sesiones activas
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

        # Configuración
        self.session_timeout = timedelta(hours=2)
        self.cleanup_interval = 300  # 5 minutos

        # Iniciar limpieza automática
        asyncio.create_task(self._cleanup_expired_sessions())

    async def create_session(
        self, criteria: SearchCriteria, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Crear nueva sesión de venta.

        Args:
            criteria: Criterios de búsqueda
            metadata: Metadatos adicionales

        Returns:
            ID de la sesión
        """
        try:
            session_id = str(uuid4())

            session = {
                "id": session_id,
                "criteria": criteria.dict(),
                "metadata": metadata or {},
                "created_at": datetime.now(),
                "last_activity": datetime.now(),
                "state": "active",
                "packages": [],
                "recommendations": [],
                "opportunities": [],
                "budgets": [],
                "history": [],
            }

            # Almacenar sesión
            self.active_sessions[session_id] = session
            await self.memory.store_session(session)

            self.logger.info(f"Nueva sesión creada: {session_id}")
            return session_id

        except Exception as e:
            self.logger.error(f"Error creando sesión: {str(e)}")
            raise

    async def update_session(
        self,
        session_id: str,
        packages: Optional[List[TravelPackage]] = None,
        criteria: Optional[SearchCriteria] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Actualizar sesión existente.

        Args:
            session_id: ID de la sesión
            packages: Nuevos paquetes encontrados
            criteria: Nuevos criterios de búsqueda
            metadata: Nuevos metadatos
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                raise ValueError(f"Sesión no encontrada: {session_id}")

            # Actualizar última actividad
            session["last_activity"] = datetime.now()

            # Actualizar paquetes si se proporcionan
            if packages:
                session["packages"] = [p.dict() for p in packages]

                # Actualizar recomendaciones
                recommendations = await self.recommendation_engine.get_recommendations(
                    packages=packages, criteria=SearchCriteria(**session["criteria"])
                )
                session["recommendations"] = [r.dict() for r in recommendations]

                # Actualizar oportunidades
                opportunities = await self.opportunity_tracker.track_opportunities(
                    packages=packages, criteria=SearchCriteria(**session["criteria"])
                )
                session["opportunities"] = [o.dict() for o in opportunities]

            # Actualizar criterios si se proporcionan
            if criteria:
                session["criteria"] = criteria.dict()

            # Actualizar metadatos si se proporcionan
            if metadata:
                session["metadata"].update(metadata)

            # Almacenar cambios
            self.active_sessions[session_id] = session
            await self.memory.update_session(session)

            self.logger.info(f"Sesión actualizada: {session_id}")

        except Exception as e:
            self.logger.error(f"Error actualizando sesión: {str(e)}")
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener datos de sesión.

        Args:
            session_id: ID de la sesión

        Returns:
            Datos de la sesión o None si no existe
        """
        try:
            # Intentar obtener de sesiones activas
            session = self.active_sessions.get(session_id)
            if session:
                return session

            # Intentar obtener de almacenamiento
            session = await self.memory.get_session(session_id)
            if session:
                self.active_sessions[session_id] = session

            return session

        except Exception as e:
            self.logger.error(f"Error obteniendo sesión: {str(e)}")
            return None

    async def close_session(self, session_id: str, status: str = "completed"):
        """
        Cerrar sesión de venta.

        Args:
            session_id: ID de la sesión
            status: Estado final (completed, cancelled, expired)
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                raise ValueError(f"Sesión no encontrada: {session_id}")

            # Actualizar estado
            session["state"] = status
            session["closed_at"] = datetime.now()

            # Almacenar sesión cerrada
            await self.memory.store_session(session)

            # Eliminar de sesiones activas
            self.active_sessions.pop(session_id, None)

            self.logger.info(f"Sesión cerrada: {session_id} ({status})")

        except Exception as e:
            self.logger.error(f"Error cerrando sesión: {str(e)}")
            raise

    async def add_budget_to_session(self, session_id: str, budget: Budget):
        """
        Agregar presupuesto a sesión.

        Args:
            session_id: ID de la sesión
            budget: Presupuesto a agregar
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                raise ValueError(f"Sesión no encontrada: {session_id}")

            # Agregar presupuesto
            session["budgets"].append(budget.dict())

            # Actualizar última actividad
            session["last_activity"] = datetime.now()

            # Almacenar cambios
            await self.update_session(
                session_id=session_id, metadata={"last_budget_id": budget.id}
            )

            self.logger.info(f"Presupuesto {budget.id} agregado a sesión {session_id}")

        except Exception as e:
            self.logger.error(f"Error agregando presupuesto: {str(e)}")
            raise

    async def add_to_history(
        self, session_id: str, action: str, data: Optional[Dict[str, Any]] = None
    ):
        """
        Agregar entrada al historial de sesión.

        Args:
            session_id: ID de la sesión
            action: Tipo de acción
            data: Datos adicionales
        """
        try:
            session = await self.get_session(session_id)
            if not session:
                raise ValueError(f"Sesión no encontrada: {session_id}")

            # Crear entrada de historial
            entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "data": data or {},
            }

            # Agregar al historial
            session["history"].append(entry)

            # Actualizar sesión
            await self.update_session(
                session_id=session_id, metadata={"last_action": action}
            )

        except Exception as e:
            self.logger.error(f"Error agregando al historial: {str(e)}")
            raise

    async def _cleanup_expired_sessions(self):
        """Limpiar sesiones expiradas periódicamente."""
        while True:
            try:
                current_time = datetime.now()

                # Verificar cada sesión activa
                for session_id, session in list(self.active_sessions.items()):
                    last_activity = session["last_activity"]
                    if isinstance(last_activity, str):
                        last_activity = datetime.fromisoformat(last_activity)

                    if current_time - last_activity > self.session_timeout:
                        await self.close_session(
                            session_id=session_id, status="expired"
                        )

                await asyncio.sleep(self.cleanup_interval)

            except Exception as e:
                self.logger.error(f"Error en limpieza de sesiones: {str(e)}")
                await asyncio.sleep(60)
