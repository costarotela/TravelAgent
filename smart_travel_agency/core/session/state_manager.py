"""
Gestor de estado de sesiones.

Este módulo implementa:
1. Gestión de estado por sesión
2. Aislamiento de datos
3. Control de modificaciones
4. Persistencia de estado
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from uuid import uuid4
import asyncio
from prometheus_client import Counter, Histogram

from ..schemas import SessionState, Budget, TravelPackage, StateSnapshot, StateChange
from ..metrics import get_metrics_collector

# Métricas
SESSION_OPERATIONS = Counter(
    "session_operations_total", "Number of session operations", ["operation_type"]
)

SESSION_LATENCY = Histogram(
    "session_operation_latency_seconds",
    "Latency of session operations",
    ["operation_type"],
)


class SessionStateManager:
    """
    Gestor de estado de sesiones.

    Responsabilidades:
    1. Crear y gestionar sesiones
    2. Mantener aislamiento de datos
    3. Controlar modificaciones
    4. Persistir estados
    """

    def __init__(self):
        """Inicializar gestor de estado."""
        self.logger = logging.getLogger(__name__)
        self.metrics = get_metrics_collector()

        # Estado en memoria
        self._active_sessions: Dict[str, SessionState] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._snapshots: Dict[str, List[StateSnapshot]] = {}

        # Configuración
        self.config = {
            "max_session_duration": 3600,  # 1 hora
            "max_snapshots": 10,  # Máximo de snapshots por sesión
            "stability_threshold": 0.8,  # 80% de estabilidad mínima
        }

    async def create_session(
        self, initial_budget: Optional[Budget] = None
    ) -> SessionState:
        """
        Crear nueva sesión.

        Args:
            initial_budget: Presupuesto inicial opcional

        Returns:
            Estado de sesión creado
        """
        try:
            session_id = str(uuid4())

            # Crear estado inicial
            session_state = SessionState(
                id=session_id,
                created_at=datetime.now(),
                is_active=True,
                budget=initial_budget,
                changes=[],
            )

            # Registrar sesión
            self._active_sessions[session_id] = session_state
            self._session_locks[session_id] = asyncio.Lock()
            self._snapshots[session_id] = []

            # Crear snapshot inicial
            if initial_budget:
                await self._create_snapshot(session_id)

            # Registrar métrica
            SESSION_OPERATIONS.labels(operation_type="create").inc()

            return session_state

        except Exception as e:
            self.logger.error(f"Error creando sesión: {e}")
            raise

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Obtener estado de sesión.

        Args:
            session_id: ID de la sesión

        Returns:
            Estado de sesión o None si no existe
        """
        try:
            return self._active_sessions.get(session_id)

        except Exception as e:
            self.logger.error(f"Error obteniendo sesión: {e}")
            return None

    async def update_session(
        self, session_id: str, budget: Budget, change_description: str
    ) -> bool:
        """
        Actualizar estado de sesión.

        Args:
            session_id: ID de la sesión
            budget: Nuevo presupuesto
            change_description: Descripción del cambio

        Returns:
            True si se actualizó correctamente
        """
        try:
            async with self._session_locks[session_id]:
                session = await self.get_session(session_id)

                if not session or not session.is_active:
                    return False

                # Validar estabilidad
                if not await self._validate_stability(session, budget):
                    return False

                # Registrar cambio
                change = StateChange(
                    timestamp=datetime.now(),
                    description=change_description,
                    previous_budget=session.budget,
                    new_budget=budget,
                )

                session.changes.append(change)
                session.budget = budget

                # Crear snapshot si es necesario
                await self._create_snapshot(session_id)

                # Registrar métrica
                SESSION_OPERATIONS.labels(operation_type="update").inc()

                return True

        except Exception as e:
            self.logger.error(f"Error actualizando sesión: {e}")
            return False

    async def close_session(self, session_id: str) -> bool:
        """
        Cerrar sesión.

        Args:
            session_id: ID de la sesión

        Returns:
            True si se cerró correctamente
        """
        try:
            async with self._session_locks[session_id]:
                session = await self.get_session(session_id)

                if not session or not session.is_active:
                    return False

                # Crear snapshot final
                await self._create_snapshot(session_id)

                # Marcar como inactiva
                session.is_active = False
                session.closed_at = datetime.now()

                # Registrar métrica
                SESSION_OPERATIONS.labels(operation_type="close").inc()

                return True

        except Exception as e:
            self.logger.error(f"Error cerrando sesión: {e}")
            return False

    async def get_snapshots(self, session_id: str) -> List[StateSnapshot]:
        """
        Obtener snapshots de sesión.

        Args:
            session_id: ID de la sesión

        Returns:
            Lista de snapshots
        """
        try:
            return self._snapshots.get(session_id, [])

        except Exception as e:
            self.logger.error(f"Error obteniendo snapshots: {e}")
            return []

    async def restore_snapshot(self, session_id: str, snapshot_id: str) -> bool:
        """
        Restaurar snapshot.

        Args:
            session_id: ID de la sesión
            snapshot_id: ID del snapshot

        Returns:
            True si se restauró correctamente
        """
        try:
            async with self._session_locks[session_id]:
                session = await self.get_session(session_id)

                if not session or not session.is_active:
                    return False

                # Buscar snapshot
                snapshots = await self.get_snapshots(session_id)
                snapshot = next((s for s in snapshots if s.id == snapshot_id), None)

                if not snapshot:
                    return False

                # Restaurar estado
                session.budget = snapshot.budget

                # Registrar cambio
                change = StateChange(
                    timestamp=datetime.now(),
                    description=f"Restored from snapshot {snapshot_id}",
                    previous_budget=session.budget,
                    new_budget=snapshot.budget,
                )

                session.changes.append(change)

                # Registrar métrica
                SESSION_OPERATIONS.labels(operation_type="restore").inc()

                return True

        except Exception as e:
            self.logger.error(f"Error restaurando snapshot: {e}")
            return False

    async def _create_snapshot(self, session_id: str) -> None:
        """Crear snapshot de estado actual."""
        try:
            session = await self.get_session(session_id)

            if not session or not session.budget:
                return

            # Crear snapshot
            snapshot = StateSnapshot(
                id=str(uuid4()),
                timestamp=datetime.now(),
                budget=session.budget.copy(),
                changes=session.changes.copy(),
            )

            # Mantener límite de snapshots
            snapshots = self._snapshots[session_id]
            if len(snapshots) >= self.config["max_snapshots"]:
                snapshots.pop(0)

            snapshots.append(snapshot)

        except Exception as e:
            self.logger.error(f"Error creando snapshot: {e}")

    async def _validate_stability(
        self, session: SessionState, new_budget: Budget
    ) -> bool:
        """Validar estabilidad del cambio."""
        try:
            if not session.budget:
                return True

            # Calcular diferencias
            price_changes = []
            for old_pkg, new_pkg in zip(session.budget.packages, new_budget.packages):
                if old_pkg.price > 0:
                    change = abs((new_pkg.price - old_pkg.price) / old_pkg.price)
                    price_changes.append(change)

            if not price_changes:
                return True

            # Validar estabilidad
            max_change = max(price_changes)
            return max_change <= (1 - self.config["stability_threshold"])

        except Exception as e:
            self.logger.error(f"Error validando estabilidad: {e}")
            return False


# Instancia global
session_manager = SessionStateManager()


async def get_session_manager() -> SessionStateManager:
    """Obtener instancia del gestor de sesiones."""
    return session_manager
