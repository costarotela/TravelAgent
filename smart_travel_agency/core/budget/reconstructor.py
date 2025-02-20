"""
Reconstrucción de presupuestos.

Este módulo implementa:
1. Reconstrucción dinámica de presupuestos
2. Manejo de cambios durante sesiones activas
3. Optimización iterativa de presupuestos
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from decimal import Decimal
from prometheus_client import Counter, Histogram

from ..schemas import (
    Budget,
    TravelPackage,
    ReconstructionStrategy,
    ReconstructionResult,
    SessionState,
)
from ..metrics import get_metrics_collector
from ..memory import get_memory_manager

# Métricas
RECONSTRUCTION_OPERATIONS = Counter(
    "budget_reconstruction_operations_total",
    "Number of reconstruction operations",
    ["operation_type", "strategy"],
)

RECONSTRUCTION_LATENCY = Histogram(
    "reconstruction_operation_latency_seconds",
    "Latency of reconstruction operations",
    ["operation_type", "strategy"],
)


class BudgetReconstructor:
    """
    Reconstrucción de presupuestos.

    Responsabilidades:
    1. Reconstruir presupuestos cuando hay cambios
    2. Mantener estabilidad durante sesiones activas
    3. Optimizar resultados iterativamente
    """

    def __init__(self):
        """Inicializar reconstructor."""
        self.logger = logging.getLogger(__name__)
        self.memory = get_memory_manager()
        self.metrics = get_metrics_collector()

        # Estrategias de reconstrucción
        self.strategies = {
            ReconstructionStrategy.PRESERVE_MARGIN: self._preserve_margin_strategy,
            ReconstructionStrategy.PRESERVE_PRICE: self._preserve_price_strategy,
            ReconstructionStrategy.ADJUST_PROPORTIONAL: self._adjust_proportional_strategy,
            ReconstructionStrategy.BEST_ALTERNATIVE: self._best_alternative_strategy,
        }

        # Umbrales de reconstrucción
        self.thresholds = {
            "price_change": 0.15,  # 15% cambio máximo
            "margin_minimum": 0.10,  # 10% margen mínimo
            "iterations_max": 3,  # Máximo de iteraciones
            "stability_score": 0.8,  # Score mínimo de estabilidad
        }

    async def reconstruct_budget(
        self,
        budget: Budget,
        changes: Dict[str, Any],
        session_state: Optional[SessionState] = None,
        strategy: Optional[ReconstructionStrategy] = None,
    ) -> ReconstructionResult:
        """
        Reconstruir presupuesto aplicando cambios.

        Args:
            budget: Presupuesto a reconstruir
            changes: Cambios a aplicar
            session_state: Estado de la sesión activa
            strategy: Estrategia de reconstrucción

        Returns:
            Resultado de la reconstrucción
        """
        try:
            start_time = datetime.now()

            # Si hay una sesión activa, validar estabilidad
            if session_state and session_state.is_active:
                stability_score = self._calculate_stability_impact(budget, changes)

                if stability_score < self.thresholds["stability_score"]:
                    return ReconstructionResult(
                        success=False,
                        error="changes_too_disruptive",
                        stability_score=stability_score,
                    )

            # Si no se especifica estrategia, seleccionar la mejor
            if not strategy:
                strategy = await self._select_best_strategy(budget, changes)

            # Aplicar estrategia de reconstrucción
            reconstruction_func = self.strategies[strategy]
            result = await reconstruction_func(budget, changes)

            # Validar resultado
            if not self._validate_reconstruction(result):
                return ReconstructionResult(
                    success=False, error="invalid_reconstruction", details=result
                )

            # Registrar métricas
            duration = (datetime.now() - start_time).total_seconds()
            RECONSTRUCTION_LATENCY.labels(
                operation_type="reconstruct", strategy=strategy.value
            ).observe(duration)

            RECONSTRUCTION_OPERATIONS.labels(
                operation_type="reconstruct", strategy=strategy.value
            ).inc()

            return ReconstructionResult(
                success=True,
                strategy_used=strategy,
                reconstructed_budget=result,
                stability_score=self._calculate_stability_score(result),
            )

        except Exception as e:
            self.logger.error(f"Error en reconstrucción: {e}")
            return ReconstructionResult(success=False, error=str(e))

    async def _preserve_margin_strategy(
        self, budget: Budget, changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estrategia: Preservar margen original.

        Ajusta el precio final para mantener el margen
        de ganancia original ante cambios en costos.
        """
        try:
            original_margin = self._calculate_margin(budget)
            modified_budget = budget.copy()

            # Aplicar cambios manteniendo margen
            for item in modified_budget.items:
                if item.id in changes.get("cost_changes", {}):
                    new_cost = changes["cost_changes"][item.id]
                    new_price = new_cost / (1 - original_margin)
                    item.price = new_price

            return modified_budget.dict()

        except Exception as e:
            self.logger.error(f"Error en estrategia preserve_margin: {e}")
            raise

    async def _preserve_price_strategy(
        self, budget: Budget, changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estrategia: Preservar precio final.

        Mantiene el precio final constante, ajustando
        el margen para absorber cambios en costos.
        """
        try:
            modified_budget = budget.copy()

            # Aplicar cambios manteniendo precio final
            for item in modified_budget.items:
                if item.id in changes.get("cost_changes", {}):
                    new_cost = changes["cost_changes"][item.id]
                    item.cost = new_cost
                    # Precio se mantiene igual, margen se ajusta

            return modified_budget.dict()

        except Exception as e:
            self.logger.error(f"Error en estrategia preserve_price: {e}")
            raise

    async def _adjust_proportional_strategy(
        self, budget: Budget, changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estrategia: Ajuste proporcional.

        Distribuye los cambios proporcionalmente entre
        precio final y margen de ganancia.
        """
        try:
            modified_budget = budget.copy()

            # Aplicar cambios distribuyendo el impacto
            for item in modified_budget.items:
                if item.id in changes.get("cost_changes", {}):
                    new_cost = changes["cost_changes"][item.id]
                    cost_diff = new_cost - item.cost

                    # Distribuir diferencia 50/50
                    item.cost = new_cost
                    item.price += cost_diff * 0.5

            return modified_budget.dict()

        except Exception as e:
            self.logger.error(f"Error en estrategia adjust_proportional: {e}")
            raise

    async def _best_alternative_strategy(
        self, budget: Budget, changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estrategia: Mejor alternativa.

        Busca y reconstruye usando el mejor paquete
        alternativo disponible.
        """
        try:
            modified_budget = budget.copy()

            # Buscar alternativas para items afectados
            for item in modified_budget.items:
                if item.id in changes.get("unavailable_items", []):
                    alternative = await self._find_best_alternative(
                        item, budget.criteria
                    )

                    if alternative:
                        # Reemplazar item con alternativa
                        item_index = modified_budget.items.index(item)
                        modified_budget.items[item_index] = alternative

            return modified_budget.dict()

        except Exception as e:
            self.logger.error(f"Error en estrategia best_alternative: {e}")
            raise

    async def _select_best_strategy(
        self, budget: Budget, changes: Dict[str, Any]
    ) -> ReconstructionStrategy:
        """Seleccionar la mejor estrategia según el caso."""
        try:
            # Si hay items no disponibles, usar alternativas
            if changes.get("unavailable_items"):
                return ReconstructionStrategy.BEST_ALTERNATIVE

            # Si hay cambios de costo significativos
            if changes.get("cost_changes"):
                max_change = max(
                    abs((new - budget.items[id].cost) / budget.items[id].cost)
                    for id, new in changes["cost_changes"].items()
                )

                if max_change > self.thresholds["price_change"]:
                    return ReconstructionStrategy.ADJUST_PROPORTIONAL
                else:
                    return ReconstructionStrategy.PRESERVE_MARGIN

            # Por defecto, preservar margen
            return ReconstructionStrategy.PRESERVE_MARGIN

        except Exception as e:
            self.logger.error(f"Error seleccionando estrategia: {e}")
            return ReconstructionStrategy.PRESERVE_MARGIN

    def _calculate_stability_impact(
        self, budget: Budget, changes: Dict[str, Any]
    ) -> float:
        """Calcular impacto en la estabilidad de la sesión."""
        try:
            impact_scores = []

            # Impacto por cambios de precio
            if changes.get("cost_changes"):
                price_changes = [
                    abs((new - budget.items[id].cost) / budget.items[id].cost)
                    for id, new in changes["cost_changes"].items()
                ]
                impact_scores.append(max(price_changes))

            # Impacto por items no disponibles
            if changes.get("unavailable_items"):
                unavailable_impact = len(changes["unavailable_items"]) / len(
                    budget.items
                )
                impact_scores.append(unavailable_impact)

            # Si no hay impactos, retornar máxima estabilidad
            if not impact_scores:
                return 1.0

            # Retornar inverso del máximo impacto
            return 1.0 - max(impact_scores)

        except Exception as e:
            self.logger.error(f"Error calculando impacto: {e}")
            return 0.0

    def _validate_reconstruction(self, reconstruction: Dict[str, Any]) -> bool:
        """Validar resultado de reconstrucción."""
        try:
            # Validar estructura básica
            if not reconstruction.get("items"):
                return False

            # Validar cada item
            for item in reconstruction["items"]:
                # Precio debe ser mayor al costo
                if item["price"] <= item["cost"]:
                    return False

                # Margen debe ser mayor al mínimo
                margin = (item["price"] - item["cost"]) / item["price"]
                if margin < self.thresholds["margin_minimum"]:
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error validando reconstrucción: {e}")
            return False

    def _calculate_stability_score(self, reconstruction: Dict[str, Any]) -> float:
        """Calcular score de estabilidad del resultado."""
        try:
            stability_factors = []

            # Estabilidad de precios
            price_changes = [
                abs((item["price"] - item["original_price"]) / item["original_price"])
                for item in reconstruction["items"]
                if "original_price" in item
            ]

            if price_changes:
                price_stability = 1.0 - (sum(price_changes) / len(price_changes))
                stability_factors.append(price_stability)

            # Estabilidad de items
            items_changed = sum(
                1
                for item in reconstruction["items"]
                if item.get("is_alternative", False)
            )
            item_stability = 1.0 - (items_changed / len(reconstruction["items"]))
            stability_factors.append(item_stability)

            # Calcular score final
            return sum(stability_factors) / len(stability_factors)

        except Exception as e:
            self.logger.error(f"Error calculando score de estabilidad: {e}")
            return 0.0

    def _calculate_margin(self, budget: Budget) -> float:
        """Calcular margen actual del presupuesto."""
        try:
            total_cost = sum(item.cost for item in budget.items)
            total_price = sum(item.price for item in budget.items)

            if total_price > 0:
                return (total_price - total_cost) / total_price
            return 0.0

        except Exception as e:
            self.logger.error(f"Error calculando margen: {e}")
            return 0.0


# Instancia global
budget_reconstructor = BudgetReconstructor()


async def get_budget_reconstructor() -> BudgetReconstructor:
    """Obtener instancia del reconstructor."""
    return budget_reconstructor
