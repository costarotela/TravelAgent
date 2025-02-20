"""
Controlador de sesión del agente de viajes.

Este módulo se enfoca en:
1. Gestión de sesiones de venta
2. Construcción de presupuestos
3. Control del vendedor
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from agent_core.managers.session_budget_manager import SessionBudgetManager
from .package_analyzer import PackageAnalyzer
from .schemas import TravelPackage, SearchCriteria


class SessionController:
    """Controlador principal de sesión."""

    def __init__(self):
        """Inicializar controlador."""
        self.logger = logging.getLogger(__name__)

        # Componentes esenciales
        self.package_analyzer = PackageAnalyzer()
        self.budget_manager = SessionBudgetManager()

        # Estado de sesiones
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    async def create_session(
        self,
        vendor_id: str,
        customer_id: str,
        initial_criteria: Optional[SearchCriteria] = None,
    ) -> str:
        """Crear nueva sesión."""
        try:
            # Crear sesión en budget manager
            session_id = await self.budget_manager.create_session(
                vendor_id, customer_id
            )

            # Inicializar estado de sesión
            self.active_sessions[session_id] = {
                "vendor_id": vendor_id,
                "customer_id": customer_id,
                "start_time": datetime.now(),
                "criteria": initial_criteria,
                "analyses": {},
            }

            return session_id

        except Exception as e:
            self.logger.error(f"Error creando sesión: {str(e)}")
            raise

    async def add_package(self, session_id: str, package: TravelPackage) -> bool:
        """Agregar paquete a la sesión."""
        if session_id not in self.active_sessions:
            raise ValueError("Sesión no encontrada")

        # Analizar paquete
        analysis = await self.package_analyzer.analyze_package(
            package=package,
            criteria=(
                self.active_sessions[session_id]["criteria"].dict()
                if self.active_sessions[session_id]["criteria"]
                else {}
            ),
        )

        # Guardar análisis
        self.active_sessions[session_id]["analyses"][package.id] = analysis

        # Agregar al presupuesto
        return await self.budget_manager.add_package(session_id, package)

    async def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Obtener estado actual de la sesión."""
        if session_id not in self.active_sessions:
            raise ValueError("Sesión no encontrada")

        session = self.active_sessions[session_id]
        budget = await self.budget_manager.get_budget(session_id)

        return {
            "session_id": session_id,
            "vendor_id": session["vendor_id"],
            "customer_id": session["customer_id"],
            "start_time": session["start_time"].isoformat(),
            "budget": budget,
            "analyses": session["analyses"],
        }

    async def close_session(self, session_id: str) -> bool:
        """Cerrar sesión."""
        if session_id not in self.active_sessions:
            raise ValueError("Sesión no encontrada")

        # Cerrar en budget manager
        await self.budget_manager.close_session(session_id)

        # Limpiar estado
        del self.active_sessions[session_id]

        return True


# Instancia global
session_controller = SessionController()


def get_session_controller() -> SessionController:
    """Obtener instancia del controlador de sesión."""
    return session_controller
