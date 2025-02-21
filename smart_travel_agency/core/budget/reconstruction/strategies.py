"""
Estrategias de reconstrucción de presupuestos.

Este módulo implementa las estrategias definidas:
1. PRESERVE_MARGIN: Mantiene margen
2. PRESERVE_PRICE: Mantiene precios
3. ADJUST_PROPORTIONALLY: Ajuste proporcional
4. BEST_ALTERNATIVE: Búsqueda inteligente
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal
import logging
from dataclasses import dataclass
from datetime import datetime

from ..schemas import Budget, BudgetItem

@dataclass
class StrategyResult:
    """Resultado de aplicar una estrategia."""
    success: bool
    changes: Dict[str, Any]
    error_message: Optional[str] = None

class ReconstructionStrategy:
    """
    Estrategia base de reconstrucción.
    
    Define la interfaz común para todas las estrategias.
    """

    def __init__(self):
        """Inicializar estrategia."""
        self.logger = logging.getLogger(__name__)

    async def apply(
        self,
        budget: Budget,
        provider_changes: Dict[str, Any]
    ) -> StrategyResult:
        """
        Aplicar estrategia.
        
        Args:
            budget: Presupuesto a reconstruir
            provider_changes: Cambios de proveedores
        """
        raise NotImplementedError

class PreserveMarginStrategy(ReconstructionStrategy):
    """
    Estrategia: Mantener margen absoluto.
    
    - Cuando el precio cambia, ajusta el costo para mantener
      el mismo margen absoluto
    """

    async def apply(
        self,
        budget: Budget,
        provider_changes: Dict[str, Any]
    ) -> StrategyResult:
        try:
            changes_applied = {}
            modified_items = []

            for item in budget.items:
                if item.id in provider_changes:
                    change = provider_changes[item.id]
                    
                    # Obtener precio original y cambio
                    original_price = Decimal(str(item.price))
                    price_change = Decimal(str(change["price_change"]))
                    
                    # Calcular nuevo precio
                    new_price = original_price + price_change
                    
                    # Mantener margen absoluto
                    original_margin = original_price - Decimal(str(item.cost))
                    new_cost = new_price - original_margin
                    
                    # Registrar cambio
                    changes_applied[item.id] = {
                        "original_price": float(original_price),
                        "new_price": float(new_price),
                        "original_margin": float(original_margin),
                        "new_cost": float(new_cost)
                    }
                    
                    # Actualizar item
                    item.price = new_price
                    item.cost = new_cost
                    modified_items.append(item)

            return StrategyResult(
                success=True,
                changes=changes_applied
            )

        except Exception as e:
            self.logger.error(f"Error en PreserveMarginStrategy: {e}")
            return StrategyResult(
                success=False,
                changes={},
                error_message=str(e)
            )

class PreservePriceStrategy(ReconstructionStrategy):
    """
    Estrategia: Mantener precio final.
    
    - Mantiene el precio final constante
    - Ajusta el margen para absorber cambios en costos
    """

    async def apply(
        self,
        budget: Budget,
        provider_changes: Dict[str, Any]
    ) -> StrategyResult:
        try:
            changes_applied = {}
            modified_items = []

            for item in budget.items:
                if item.id in provider_changes:
                    change = provider_changes[item.id]
                    
                    # Precio se mantiene igual
                    original_price = item.price
                    
                    # Aplicar cambio de costo
                    cost_change = Decimal(str(change["cost_change"]))
                    new_cost = item.cost + cost_change
                    
                    # Nuevo margen = precio - nuevo costo
                    new_margin = original_price - new_cost
                    
                    # Registrar cambio
                    changes_applied[item.id] = {
                        "price": float(original_price),
                        "original_cost": float(item.cost),
                        "new_cost": float(new_cost),
                        "new_margin": float(new_margin)
                    }
                    
                    # Actualizar item
                    item.cost = new_cost
                    modified_items.append(item)

            return StrategyResult(
                success=True,
                changes=changes_applied
            )

        except Exception as e:
            self.logger.error(f"Error en PreservePriceStrategy: {e}")
            return StrategyResult(
                success=False,
                changes={},
                error_message=str(e)
            )

class AdjustProportionallyStrategy(ReconstructionStrategy):
    """
    Estrategia: Ajuste proporcional.
    
    - Distribuye los cambios proporcionalmente entre
      precio final y margen de ganancia
    """

    async def apply(
        self,
        budget: Budget,
        provider_changes: Dict[str, Any]
    ) -> StrategyResult:
        try:
            changes_applied = {}
            modified_items = []

            for item in budget.items:
                if item.id in provider_changes:
                    change = provider_changes[item.id]
                    
                    # Obtener cambio de costo
                    cost_change = Decimal(str(change["cost_change"]))
                    
                    # Distribuir el impacto 50/50
                    price_adjustment = cost_change * Decimal("0.5")
                    new_cost = item.cost + cost_change
                    new_price = item.price + price_adjustment
                    
                    # Registrar cambio
                    changes_applied[item.id] = {
                        "original_cost": float(item.cost),
                        "new_cost": float(new_cost),
                        "original_price": float(item.price),
                        "new_price": float(new_price),
                        "cost_change": float(cost_change),
                        "price_adjustment": float(price_adjustment)
                    }
                    
                    # Actualizar item
                    item.cost = new_cost
                    item.price = new_price
                    modified_items.append(item)

            return StrategyResult(
                success=True,
                changes=changes_applied
            )

        except Exception as e:
            self.logger.error(f"Error en AdjustProportionallyStrategy: {e}")
            return StrategyResult(
                success=False,
                changes={},
                error_message=str(e)
            )

class BestAlternativeStrategy(ReconstructionStrategy):
    """
    Estrategia: Búsqueda inteligente.
    
    - Busca y reconstruye usando el mejor paquete alternativo
    - Evalúa calidad y precio de alternativas
    - Solo reemplaza si la alternativa es mejor
    """

    async def apply(
        self,
        budget: Budget,
        provider_changes: Dict[str, Any]
    ) -> StrategyResult:
        try:
            changes_applied = {}
            modified_items = []

            for item in budget.items:
                if item.id in provider_changes:
                    change = provider_changes[item.id]
                    
                    # Buscar alternativa
                    alternative = await self._find_best_alternative(
                        item=item,
                        constraints=change.get("constraints", {})
                    )
                    
                    if alternative:
                        # Evaluar scores
                        original_score = self._calculate_item_score(item)
                        alternative_score = self._calculate_item_score(alternative)
                        
                        if alternative_score > original_score:
                            # Registrar cambio
                            changes_applied[item.id] = {
                                "original_item": item.dict(),
                                "alternative_item": alternative.dict(),
                                "original_score": original_score,
                                "alternative_score": alternative_score,
                                "reason": "better_alternative"
                            }
                            
                            # Actualizar item
                            modified_items.append(alternative)
                        else:
                            changes_applied[item.id] = {
                                "message": "alternative_found_but_not_better",
                                "original_score": original_score,
                                "alternative_score": alternative_score
                            }
                    else:
                        changes_applied[item.id] = {
                            "error": "no_alternative_found"
                        }

            return StrategyResult(
                success=True,
                changes=changes_applied
            )

        except Exception as e:
            self.logger.error(f"Error en BestAlternativeStrategy: {e}")
            return StrategyResult(
                success=False,
                changes={},
                error_message=str(e)
            )

    async def _find_best_alternative(
        self,
        item: BudgetItem,
        constraints: Dict[str, Any]
    ) -> Optional[BudgetItem]:
        """
        Buscar mejor alternativa para un item.
        
        Args:
            item: Item original
            constraints: Restricciones a cumplir
        """
        # TODO: Implementar búsqueda real de alternativas
        return None

    def _calculate_item_score(self, item: BudgetItem) -> float:
        """
        Calcular score de un item.
        
        Considera:
        - Precio
        - Rating
        - Disponibilidad
        """
        score = 0.0
        
        # Factor de precio (menor es mejor)
        if item.price > 0:
            price_score = 1.0 / float(item.price)
            score += price_score * 0.4  # 40% del score
        
        # Factor de rating
        if item.rating:
            score += (item.rating / 5.0) * 0.4  # 40% del score
        
        # Factor de disponibilidad
        if hasattr(item, 'availability') and item.availability:
            score += item.availability * 0.2  # 20% del score
        
        return score

# Mapa de estrategias disponibles
STRATEGIES = {
    "preserve_margin": PreserveMarginStrategy(),
    "preserve_price": PreservePriceStrategy(),
    "adjust_proportionally": AdjustProportionallyStrategy(),
    "best_alternative": BestAlternativeStrategy()
}
