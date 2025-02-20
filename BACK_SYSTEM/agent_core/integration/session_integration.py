"""
Integración de sesiones y reconstrucción.

Este módulo maneja:
1. Control de sesiones
2. Integración con reconstrucción
3. Manejo de estados
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from pathlib import Path

from agent_core.managers.session_budget_manager import SessionBudgetManager
from agent_core.reconstruction.budget_builder import BudgetBuilder
from agent_core.reconstruction.version_manager import VersionManager
from agent_core.reconstruction.history_manager import HistoryManager


class SessionIntegration:
    """Integrador de sesiones y reconstrucción."""

    def __init__(
        self,
        budget_manager: SessionBudgetManager,
        budget_builder: BudgetBuilder,
        version_manager: VersionManager,
        history_manager: HistoryManager,
    ):
        """Inicializar integrador."""
        self.logger = logging.getLogger(__name__)
        self.budget_manager = budget_manager
        self.budget_builder = budget_builder
        self.version_manager = version_manager
        self.history_manager = history_manager

    async def initialize_session(
        self, vendor_id: str, customer_id: str, initial_data: Dict[str, Any]
    ) -> str:
        """Inicializar nueva sesión."""
        try:
            # Crear sesión
            session_id = await self.budget_manager.create_session(
                vendor_id=vendor_id, customer_id=customer_id
            )

            # Crear checkpoint inicial
            await self.budget_builder.create_checkpoint(
                session_id=session_id,
                budget_data=initial_data,
                metadata={
                    "source": "session_init",
                    "vendor_id": vendor_id,
                    "customer_id": customer_id,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            # Registrar evento de inicio
            await self.history_manager.record_change(
                session_id=session_id,
                change_type="session_start",
                details={
                    "vendor_id": vendor_id,
                    "customer_id": customer_id,
                    "initial_data": initial_data,
                },
                user_id=vendor_id,
            )

            return session_id

        except Exception as e:
            self.logger.error(f"Error inicializando sesión: {str(e)}")
            raise

    async def modify_budget(
        self, session_id: str, modifications: List[Dict[str, Any]], user_id: str
    ) -> bool:
        """Aplicar modificaciones al presupuesto."""
        try:
            # Obtener versión actual
            current_version = await self.budget_manager.get_budget(
                session_id=session_id
            )

            # Crear checkpoint pre-modificación
            await self.budget_builder.create_checkpoint(
                session_id=session_id,
                budget_data=current_version,
                metadata={
                    "source": "pre_modification",
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            # Aplicar modificaciones
            modified_budget = await self.budget_builder.apply_changes(
                session_id=session_id,
                base_version=current_version["version"],
                changes=modifications,
            )

            # Validar estado resultante
            if not await self.budget_builder.validate_state(
                session_id=session_id, budget_data=modified_budget
            ):
                raise ValueError("Estado inválido después de modificaciones")

            # Registrar cambios
            for mod in modifications:
                await self.history_manager.record_change(
                    session_id=session_id,
                    change_type=mod["change_type"],
                    details=mod["details"],
                    user_id=user_id,
                )

            # Crear checkpoint post-modificación
            await self.budget_builder.create_checkpoint(
                session_id=session_id,
                budget_data=modified_budget,
                metadata={
                    "source": "post_modification",
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                    "modifications_applied": len(modifications),
                },
            )

            return True

        except Exception as e:
            self.logger.error(f"Error modificando presupuesto: {str(e)}")
            raise

    async def restore_version(
        self, session_id: str, version_id: str, user_id: str
    ) -> bool:
        """Restaurar versión específica del presupuesto."""
        try:
            # Reconstruir presupuesto
            restored_budget = await self.budget_builder.reconstruct_budget(
                session_id=session_id, target_version=version_id
            )

            # Validar estado
            if not await self.budget_builder.validate_state(
                session_id=session_id, budget_data=restored_budget
            ):
                raise ValueError("Estado inválido en versión restaurada")

            # Registrar restauración
            await self.history_manager.record_change(
                session_id=session_id,
                change_type="version_restore",
                details={
                    "restored_version": version_id,
                    "budget_state": restored_budget,
                },
                user_id=user_id,
            )

            # Crear checkpoint de restauración
            await self.budget_builder.create_checkpoint(
                session_id=session_id,
                budget_data=restored_budget,
                metadata={
                    "source": "version_restore",
                    "restored_from": version_id,
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return True

        except Exception as e:
            self.logger.error(f"Error restaurando versión: {str(e)}")
            raise

    async def close_session(self, session_id: str, user_id: str) -> bool:
        """Cerrar sesión."""
        try:
            # Obtener estado final
            final_state = await self.budget_manager.get_budget(session_id=session_id)

            # Crear checkpoint final
            await self.budget_builder.create_checkpoint(
                session_id=session_id,
                budget_data=final_state,
                metadata={
                    "source": "session_close",
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            # Registrar cierre
            await self.history_manager.record_change(
                session_id=session_id,
                change_type="session_end",
                details={"final_state": final_state},
                user_id=user_id,
            )

            # Cerrar sesión
            return await self.budget_manager.close_session(session_id=session_id)

        except Exception as e:
            self.logger.error(f"Error cerrando sesión: {str(e)}")
            raise
