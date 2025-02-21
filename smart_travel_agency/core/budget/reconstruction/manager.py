"""
Orquestación de reconstrucción de presupuestos.

Este módulo coordina el proceso de reconstrucción:
1. Verifica que el paquete esté completo
2. Obtiene datos de proveedores
3. Coordina la reconstrucción
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from dataclasses import dataclass, field

from ..reconstructor import (
    get_budget_reconstructor,
    ReconstructionStrategy
)
from .models import ReconstructionResult
from ..manager import get_budget_manager
from .session_manager import get_session_manager

class BudgetReconstructionManager:
    """
    Coordinador de reconstrucción de presupuestos.
    
    Responsabilidades:
    1. Verificar completitud del paquete
    2. Coordinar con proveedores
    3. Orquestar reconstrucción
    """

    def __init__(self):
        """Inicializar manager."""
        self.logger = logging.getLogger(__name__)
        self._reconstructor = get_budget_reconstructor()
        self._session_manager = get_session_manager()
        self._reconstruction_history: Dict[str, List[ReconstructionResult]] = {}

    async def apply_reconstruction(
        self,
        budget_id: str,
        provider_changes: Dict[str, Any],
        strategy_name: str = "preserve_package"
    ) -> ReconstructionResult:
        """
        Aplicar reconstrucción a un presupuesto.
        
        Args:
            budget_id: ID del presupuesto
            provider_changes: Cambios confirmados de proveedores
            strategy_name: Nombre de la estrategia
        """
        try:
            # 1. Obtener presupuesto
            budget = await get_budget_manager().get_budget(budget_id)
            if not budget:
                raise ValueError(f"Presupuesto {budget_id} no encontrado")

            # 2. Convertir estrategia
            strategy_map = {
                "preserve_package": ReconstructionStrategy.PRESERVE_PACKAGE,
                "find_alternatives": ReconstructionStrategy.FIND_ALTERNATIVES,
                "adjust_services": ReconstructionStrategy.ADJUST_SERVICES
            }
            strategy = strategy_map.get(strategy_name.lower())
            if not strategy:
                raise ValueError(f"Estrategia {strategy_name} no válida")

            # 3. Delegar reconstrucción al CORE
            result = await self._reconstructor.reconstruct_budget(
                budget=budget,
                provider_changes=provider_changes,
                strategy=strategy
            )

            # 4. Registrar en historial
            if budget_id not in self._reconstruction_history:
                self._reconstruction_history[budget_id] = []
            self._reconstruction_history[budget_id].append(result)

            return result

        except Exception as e:
            self.logger.error(f"Error en reconstrucción: {e}")
            return ReconstructionResult(
                budget_id=budget_id,
                success=False,
                changes_applied={},
                strategy_used=strategy_name,
                error_message=str(e)
            )

    async def get_reconstruction_history(
        self, 
        budget_id: str
    ) -> List[ReconstructionResult]:
        """Obtener historial de reconstrucciones."""
        return self._reconstruction_history.get(budget_id, [])

# Instancia global
_manager: Optional[BudgetReconstructionManager] = None

def get_reconstruction_manager() -> BudgetReconstructionManager:
    """Obtener instancia del manager."""
    global _manager
    if not _manager:
        _manager = BudgetReconstructionManager()
    return _manager
