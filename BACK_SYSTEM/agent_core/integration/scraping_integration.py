"""
Integración entre sistema de scraping y sesiones.

Este módulo maneja:
1. Conexión entre scraping y sesiones
2. Control de actualizaciones
3. Manejo de cambios entre sesiones
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from pathlib import Path

from agent_core.scrapers.session_manager import ScrapingSessionManager
from agent_core.scrapers.change_detector import ChangeDetector
from agent_core.managers.session_budget_manager import SessionBudgetManager
from agent_core.reconstruction.budget_builder import BudgetBuilder


class ScrapingIntegration:
    """Integrador de scraping y sesiones."""

    def __init__(
        self,
        scraping_manager: ScrapingSessionManager,
        change_detector: ChangeDetector,
        budget_manager: SessionBudgetManager,
        budget_builder: BudgetBuilder,
    ):
        """Inicializar integrador."""
        self.logger = logging.getLogger(__name__)
        self.scraping_manager = scraping_manager
        self.change_detector = change_detector
        self.budget_manager = budget_manager
        self.budget_builder = budget_builder

    async def capture_initial_data(
        self, session_id: str, search_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Capturar datos iniciales para una sesión."""
        try:
            # Iniciar sesión de scraping
            scraping_session = await self.scraping_manager.create_session(
                session_id=session_id, criteria=search_criteria
            )

            # Obtener datos iniciales
            initial_data = await self.scraping_manager.get_session_data(
                session_id=session_id
            )

            # Crear checkpoint inicial
            await self.budget_builder.create_checkpoint(
                session_id=session_id,
                budget_data=initial_data,
                metadata={
                    "source": "initial_capture",
                    "timestamp": datetime.now().isoformat(),
                    "criteria": search_criteria,
                },
            )

            return initial_data

        except Exception as e:
            self.logger.error(f"Error capturando datos iniciales: {str(e)}")
            raise

    async def process_changes(self, session_id: str) -> List[Dict[str, Any]]:
        """Procesar cambios detectados fuera de sesión."""
        try:
            # Verificar cambios
            changes = await self.change_detector.detect_changes(session_id=session_id)

            if not changes:
                return []

            # Obtener presupuesto actual
            current_budget = await self.budget_manager.get_budget(session_id=session_id)

            # Crear checkpoint antes de aplicar cambios
            await self.budget_builder.create_checkpoint(
                session_id=session_id,
                budget_data=current_budget,
                metadata={
                    "source": "pre_changes",
                    "timestamp": datetime.now().isoformat(),
                },
            )

            # Aplicar cambios
            updated_budget = await self.budget_builder.apply_changes(
                session_id=session_id,
                base_version=current_budget["version"],
                changes=changes,
            )

            # Validar estado resultante
            if not await self.budget_builder.validate_state(
                session_id=session_id, budget_data=updated_budget
            ):
                raise ValueError("Estado inválido después de aplicar cambios")

            # Crear checkpoint con cambios aplicados
            await self.budget_builder.create_checkpoint(
                session_id=session_id,
                budget_data=updated_budget,
                metadata={
                    "source": "post_changes",
                    "timestamp": datetime.now().isoformat(),
                    "changes_applied": len(changes),
                },
            )

            return changes

        except Exception as e:
            self.logger.error(f"Error procesando cambios: {str(e)}")
            raise

    async def validate_session_data(self, session_id: str) -> bool:
        """Validar datos de sesión."""
        try:
            # Obtener datos actuales
            current_data = await self.scraping_manager.get_session_data(
                session_id=session_id
            )

            # Obtener presupuesto actual
            current_budget = await self.budget_manager.get_budget(session_id=session_id)

            # Comparar datos
            for package in current_budget["packages"]:
                pkg_id = package["id"]
                if pkg_id in current_data["packages"]:
                    scraped_pkg = current_data["packages"][pkg_id]

                    # Verificar cambios críticos
                    if package["price"] != scraped_pkg["price"]:
                        return False

                    if package["availability"] != scraped_pkg["availability"]:
                        return False

            return True

        except Exception as e:
            self.logger.error(f"Error validando datos de sesión: {str(e)}")
            return False

    async def synchronize_data(self, session_id: str) -> bool:
        """Sincronizar datos entre sesiones."""
        try:
            # Validar datos actuales
            if not await self.validate_session_data(session_id):
                # Procesar cambios si hay inconsistencias
                changes = await self.process_changes(session_id)
                return len(changes) > 0

            return True

        except Exception as e:
            self.logger.error(f"Error sincronizando datos: {str(e)}")
            return False
