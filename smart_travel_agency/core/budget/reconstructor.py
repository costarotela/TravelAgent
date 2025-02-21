"""
Reconstrucción de presupuestos.

Este módulo implementa la lógica CORE de reconstrucción de presupuestos.
Solo se activa cuando:
1. El paquete está completamente definido
2. Hay cambios confirmados de proveedores
3. Se requiere mantener la estructura del paquete
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal
import logging
from datetime import datetime
from dataclasses import dataclass
from enum import Enum, auto

from ..schemas import (
    Budget,
    BudgetItem,
    SessionState,
)

from .reconstruction.models import ReconstructionResult

# Estrategias de reconstrucción alineadas con el negocio
class ReconstructionStrategy(Enum):
    PRESERVE_MARGIN = auto()      # Mantiene margen absoluto
    PRESERVE_PRICE = auto()       # Mantiene precio final
    ADJUST_PROPORTIONALLY = auto()  # Ajuste proporcional
    BEST_ALTERNATIVE = auto()     # Búsqueda inteligente

class BudgetReconstructor:
    """
    Reconstrucción de presupuestos.

    Responsabilidades:
    1. Reconstruir presupuestos con cambios confirmados
    2. Mantener estabilidad durante la venta
    3. Garantizar coherencia del paquete
    """

    def __init__(self):
        """Inicializar reconstructor."""
        self.logger = logging.getLogger(__name__)
        
        # Estrategias de reconstrucción
        self.strategies = {
            ReconstructionStrategy.PRESERVE_MARGIN: self._preserve_margin_strategy,
            ReconstructionStrategy.PRESERVE_PRICE: self._preserve_price_strategy,
            ReconstructionStrategy.ADJUST_PROPORTIONALLY: self._adjust_proportionally_strategy,
            ReconstructionStrategy.BEST_ALTERNATIVE: self._best_alternative_strategy
        }

    async def reconstruct_budget(
        self,
        budget: Budget,
        provider_changes: Dict[str, Any],
        strategy: Optional[ReconstructionStrategy] = None,
    ) -> ReconstructionResult:
        """
        Reconstruir presupuesto con cambios confirmados.
        
        Args:
            budget: Presupuesto completamente definido
            provider_changes: Cambios confirmados de proveedores
            strategy: Estrategia específica (opcional)
            
        Returns:
            ReconstructionResult con el resultado
        """
        try:
            # 1. Validar presupuesto completo
            if not self._is_package_complete(budget):
                raise ValueError("El paquete debe estar completamente definido")

            # 2. Validar cambios de proveedores
            if not self._are_changes_valid(provider_changes):
                raise ValueError("Los cambios deben estar confirmados por proveedores")

            # 3. Seleccionar estrategia
            if not strategy:
                strategy = self._select_best_strategy(budget, provider_changes)

            # 4. Aplicar estrategia
            result = await self.strategies[strategy](budget, provider_changes)

            # 5. Validar resultado
            if not self._is_result_valid(result):
                raise ValueError("El resultado no mantiene la coherencia del paquete")

            return ReconstructionResult(
                budget_id=budget.id,
                success=True,
                changes_applied=result.changes,
                strategy_used=strategy.name,
                error_message=None
            )

        except Exception as e:
            self.logger.error(f"Error en reconstrucción: {str(e)}")
            return ReconstructionResult(
                budget_id=budget.id,
                success=False,
                changes_applied={},
                strategy_used=strategy.name if strategy else "none",
                error_message=str(e)
            )

    async def _preserve_margin_strategy(
        self, 
        budget: Budget, 
        changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estrategia: Mantener margen absoluto.
        
        - Cuando el precio cambia, ajusta el costo para mantener
          el mismo margen absoluto
        """
        from .reconstruction.strategies import STRATEGIES
        return await STRATEGIES["preserve_margin"].apply(budget, changes)

    async def _preserve_price_strategy(
        self, 
        budget: Budget, 
        changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estrategia: Mantener precio final.
        
        - Mantiene el precio final constante
        - Ajusta el margen para absorber cambios en costos
        """
        from .reconstruction.strategies import STRATEGIES
        return await STRATEGIES["preserve_price"].apply(budget, changes)

    async def _adjust_proportionally_strategy(
        self, 
        budget: Budget, 
        changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estrategia: Ajuste proporcional.
        
        - Distribuye los cambios proporcionalmente entre
          precio final y margen de ganancia
        """
        from .reconstruction.strategies import STRATEGIES
        return await STRATEGIES["adjust_proportionally"].apply(budget, changes)

    async def _best_alternative_strategy(
        self, 
        budget: Budget, 
        changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estrategia: Búsqueda inteligente.
        
        - Busca y reconstruye usando el mejor paquete alternativo
        - Evalúa calidad y precio de alternativas
        - Solo reemplaza si la alternativa es mejor
        """
        from .reconstruction.strategies import STRATEGIES
        return await STRATEGIES["best_alternative"].apply(budget, changes)

    def _is_package_complete(self, budget: Budget) -> bool:
        """Verificar si el paquete está completamente definido."""
        if not budget or not budget.items:
            return False
            
        for item in budget.items:
            if not item.price or not item.cost:
                return False
                
        return True

    def _are_changes_valid(self, changes: Dict[str, Any]) -> bool:
        """Verificar si los cambios están confirmados por proveedores."""
        if not changes:
            return False
            
        for item_id, change in changes.items():
            if not isinstance(change, dict):
                return False
            if "price_change" not in change and "cost_change" not in change:
                return False
                
        return True

    def _select_best_strategy(
        self, 
        budget: Budget, 
        changes: Dict[str, Any]
    ) -> ReconstructionStrategy:
        """
        Seleccionar la mejor estrategia según el caso.
        
        Criterios:
        1. Si hay cambios significativos de precio: BEST_ALTERNATIVE
        2. Si hay cambios moderados: ADJUST_PROPORTIONALLY
        3. Si el margen es crítico: PRESERVE_MARGIN
        4. Por defecto: PRESERVE_PRICE
        """
        try:
            # Calcular cambio máximo
            max_change = 0.0
            for change in changes.values():
                if "price_change" in change:
                    pct = abs(float(change["price_change"])) / 100
                    max_change = max(max_change, pct)
                if "cost_change" in change:
                    pct = abs(float(change["cost_change"])) / 100
                    max_change = max(max_change, pct)

            # Seleccionar estrategia
            if max_change > 0.15:  # Cambio mayor al 15%
                return ReconstructionStrategy.BEST_ALTERNATIVE
            elif max_change > 0.05:  # Cambio mayor al 5%
                return ReconstructionStrategy.ADJUST_PROPORTIONALLY
            elif self._is_margin_critical(budget):
                return ReconstructionStrategy.PRESERVE_MARGIN
            else:
                return ReconstructionStrategy.PRESERVE_PRICE

        except Exception as e:
            self.logger.error(f"Error seleccionando estrategia: {e}")
            return ReconstructionStrategy.PRESERVE_PRICE

    def _is_margin_critical(self, budget: Budget) -> bool:
        """Verificar si el margen está en nivel crítico."""
        try:
            for item in budget.items:
                margin = (item.price - item.cost) / item.price
                if margin < 0.10:  # Margen menor al 10%
                    return True
            return False
        except:
            return False

    def _is_result_valid(self, result: Dict[str, Any]) -> bool:
        """Validar que el resultado mantiene la coherencia del paquete."""
        if not result or not isinstance(result, dict):
            return False
            
        if "success" not in result or not result["success"]:
            return False
            
        if "changes" not in result:
            return False
            
        return True

# Instancia global
_reconstructor: Optional[BudgetReconstructor] = None

def get_budget_reconstructor() -> BudgetReconstructor:
    """Obtener instancia del reconstructor."""
    global _reconstructor
    if not _reconstructor:
        _reconstructor = BudgetReconstructor()
    return _reconstructor
