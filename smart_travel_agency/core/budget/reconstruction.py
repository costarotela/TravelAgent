"""
Sistema avanzado de reconstrucción de presupuestos.

Este módulo implementa:
1. Análisis de impacto de cambios
2. Reconstrucción inteligente
3. Preservación de estabilidad
4. Sugerencias de alternativas
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
import logging
from dataclasses import dataclass
from prometheus_client import Counter, Histogram, Gauge

# Métricas
RECONSTRUCTION_OPERATIONS = Counter(
    "reconstruction_operations_total",
    "Number of reconstruction operations",
    ["operation_type", "strategy"],
)

RECONSTRUCTION_LATENCY = Histogram(
    "reconstruction_operation_latency_seconds",
    "Latency of reconstruction operations",
    ["operation_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
)

ACTIVE_RECONSTRUCTIONS = Gauge(
    "active_reconstructions_total", "Number of active reconstruction processes"
)

IMPACT_SEVERITY = Histogram(
    "reconstruction_impact_severity",
    "Severity of changes requiring reconstruction",
    buckets=[0.1, 0.3, 0.5, 0.7, 0.9],
)


class ReconstructionStrategy:
    """Estrategias de reconstrucción de presupuestos."""

    PRESERVE_MARGIN = "preserve_margin"
    PRESERVE_PRICE = "preserve_price"
    ADJUST_PROPORTIONALLY = "adjust_proportionally"
    BEST_ALTERNATIVE = "best_alternative"


@dataclass
class AnalysisResult:
    """Resultado del análisis de impacto."""

    budget_id: str
    package_id: str
    impact_level: float
    changes: List[Dict[str, Any]]
    price_impact: float
    recommendations: List[str]
    timestamp: datetime = None

    def __post_init__(self):
        self.timestamp = datetime.now()


class BudgetReconstructionManager:
    """
    Gestor avanzado de reconstrucción de presupuestos.
    """

    def __init__(self):
        """Inicializar gestor."""
        self.logger = logging.getLogger(__name__)
        self._reconstruction_tasks: Dict[str, asyncio.Task] = {}

        # Configuración
        self.impact_threshold = 0.7  # Umbral para impacto alto
        self.similarity_threshold = 0.7  # Umbral para alternativas
        self.price_change_threshold = Decimal("0.05")  # 5% cambio significativo

        # Iniciar tarea de limpieza
        asyncio.create_task(self._cleanup_task())

    async def analyze_impact(
        self, budget_id: str, changes: Dict[str, Any]
    ) -> AnalysisResult:
        """
        Analizar impacto de cambios.

        Args:
            budget_id: ID del presupuesto
            changes: Cambios detectados

        Returns:
            Resultado del análisis
        """
        start_time = datetime.now()
        try:
            severity = self._calculate_severity(changes)
            affected = self._identify_affected_components(changes)

            IMPACT_SEVERITY.observe(severity)

            recommendations = []
            if severity >= self.impact_threshold:
                strategy = self._determine_strategy(changes)
                recommendations.append(strategy)

            return AnalysisResult(
                budget_id=budget_id,
                package_id=changes.get("package_id", ""),
                impact_level=severity,
                changes=[changes],
                price_impact=self._calculate_price_impact(changes),
                recommendations=recommendations,
            )

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            RECONSTRUCTION_LATENCY.labels(operation_type="analyze").observe(duration)

    async def reconstruct_budget(
        self, budget_id: str, changes: Dict[str, Any], strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reconstruir presupuesto.

        Args:
            budget_id: ID del presupuesto
            changes: Cambios detectados
            strategy: Estrategia a usar

        Returns:
            Presupuesto reconstruido
        """
        start_time = datetime.now()
        ACTIVE_RECONSTRUCTIONS.inc()

        try:
            impact = await self.analyze_impact(budget_id, changes)

            if not strategy:
                strategy = (
                    impact.recommendations[0]
                    if impact.recommendations
                    else ReconstructionStrategy.ADJUST_PROPORTIONALLY
                )

            reconstruction_method = self._get_reconstruction_method(strategy)
            updated_budget = await reconstruction_method(budget_id, changes, impact)

            RECONSTRUCTION_OPERATIONS.labels(
                operation_type="reconstruct", strategy=strategy
            ).inc()

            return updated_budget

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            RECONSTRUCTION_LATENCY.labels(operation_type="reconstruct").observe(
                duration
            )
            ACTIVE_RECONSTRUCTIONS.dec()

    async def suggest_alternatives(
        self, budget_id: str, changes: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Sugerir alternativas.

        Args:
            budget_id: ID del presupuesto
            changes: Cambios detectados

        Returns:
            Lista de alternativas
        """
        start_time = datetime.now()
        try:
            impact = await self.analyze_impact(budget_id, changes)

            if impact.impact_level < self.impact_threshold:
                return []

            # TODO: Implementar búsqueda de alternativas
            alternatives = []

            RECONSTRUCTION_OPERATIONS.labels(
                operation_type="suggest", strategy="alternatives"
            ).inc()

            return alternatives

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            RECONSTRUCTION_LATENCY.labels(operation_type="suggest").observe(duration)

    def _calculate_severity(self, changes: Dict[str, Any]) -> float:
        """Calcular severidad de cambios."""
        severity = 0.0
        weights = {"price": 0.6, "availability": 0.2, "dates": 0.1, "features": 0.1}

        if "price" in changes:
            price_change = changes["price"]
            percentage = abs(price_change.get("percentage", 0))
            severity += weights["price"] * min(percentage / 10, 1.0)

        if "availability" in changes:
            severity += weights["availability"]

        if "dates" in changes:
            dates_change = changes["dates"]
            days_diff = abs(dates_change.get("difference_days", 0))
            severity += weights["dates"] * min(days_diff / 7, 1.0)

        if "features" in changes:
            severity += weights["features"]

        return min(severity, 1.0)

    def _identify_affected_components(self, changes: Dict[str, Any]) -> List[str]:
        """Identificar componentes afectados."""
        components = []

        if "price" in changes:
            components.append("price")
        if "availability" in changes:
            components.append("availability")
        if "dates" in changes:
            components.append("dates")
        if "features" in changes:
            components.append("features")

        return components

    def _calculate_price_impact(self, changes: Dict[str, Any]) -> float:
        """Calcular impacto en precio."""
        if "price" not in changes:
            return 0.0

        price_change = changes["price"]
        return abs(price_change.get("percentage", 0)) / 100

    def _determine_strategy(self, changes: Dict[str, Any]) -> str:
        """Determinar mejor estrategia."""
        if "price" in changes:
            price_change = changes["price"]
            if abs(price_change.get("percentage", 0)) > 20:
                return ReconstructionStrategy.BEST_ALTERNATIVE
            elif abs(price_change.get("percentage", 0)) > 10:
                return ReconstructionStrategy.PRESERVE_MARGIN
            else:
                return ReconstructionStrategy.ADJUST_PROPORTIONALLY

        return ReconstructionStrategy.PRESERVE_PRICE

    def _get_reconstruction_method(self, strategy: str):
        """Obtener método de reconstrucción."""
        methods = {
            ReconstructionStrategy.PRESERVE_MARGIN: self._reconstruct_preserve_margin,
            ReconstructionStrategy.PRESERVE_PRICE: self._reconstruct_preserve_price,
            ReconstructionStrategy.ADJUST_PROPORTIONALLY: self._reconstruct_adjust_proportionally,
            ReconstructionStrategy.BEST_ALTERNATIVE: self._reconstruct_best_alternative,
        }
        return methods.get(strategy, self._reconstruct_adjust_proportionally)

    async def _reconstruct_preserve_margin(
        self, budget_id: str, changes: Dict[str, Any], impact: AnalysisResult
    ) -> Dict[str, Any]:
        """
        Reconstruir preservando margen.

        Esta estrategia mantiene el margen de ganancia original
        ajustando el precio final según los cambios en costos.
        """
        try:
            # Obtener presupuesto original
            budget = await self.budget_manager.get_budget(budget_id)
            if not budget:
                raise ValueError(f"Presupuesto {budget_id} no encontrado")

            # Calcular margen original
            original_cost = Decimal(str(budget["cost"]))
            original_price = Decimal(str(budget["final_price"]))
            original_margin = (original_price - original_cost) / original_cost

            # Aplicar cambios al costo
            if "price" in changes:
                price_change = changes["price"]
                new_cost = original_cost * (
                    1 + Decimal(str(price_change["percentage"])) / 100
                )
            else:
                new_cost = original_cost

            # Recalcular precio manteniendo margen
            new_price = new_cost * (1 + original_margin)

            # Actualizar presupuesto
            updated_budget = budget.copy()
            updated_budget["cost"] = float(new_cost)
            updated_budget["final_price"] = float(new_price)
            updated_budget["reconstruction_info"] = {
                "strategy": ReconstructionStrategy.PRESERVE_MARGIN,
                "original_margin": float(original_margin),
                "timestamp": datetime.now().isoformat(),
            }

            return updated_budget

        except Exception as e:
            self.logger.error(f"Error en reconstrucción preserve_margin: {e}")
            raise

    async def _reconstruct_preserve_price(
        self, budget_id: str, changes: Dict[str, Any], impact: AnalysisResult
    ) -> Dict[str, Any]:
        """
        Reconstruir preservando precio.

        Esta estrategia mantiene el precio final ajustando
        el margen para absorber los cambios en costos.
        """
        try:
            # Obtener presupuesto original
            budget = await self.budget_manager.get_budget(budget_id)
            if not budget:
                raise ValueError(f"Presupuesto {budget_id} no encontrado")

            original_price = Decimal(str(budget["final_price"]))
            original_cost = Decimal(str(budget["cost"]))

            # Aplicar cambios al costo
            if "price" in changes:
                price_change = changes["price"]
                new_cost = original_cost * (
                    1 + Decimal(str(price_change["percentage"])) / 100
                )
            else:
                new_cost = original_cost

            # Calcular nuevo margen
            new_margin = (original_price - new_cost) / new_cost

            # Verificar si el margen es aceptable
            if new_margin < Decimal("0.05"):  # Mínimo 5% de margen
                raise ValueError("Margen resultante demasiado bajo")

            # Actualizar presupuesto
            updated_budget = budget.copy()
            updated_budget["cost"] = float(new_cost)
            updated_budget["final_price"] = float(original_price)
            updated_budget["reconstruction_info"] = {
                "strategy": ReconstructionStrategy.PRESERVE_PRICE,
                "new_margin": float(new_margin),
                "timestamp": datetime.now().isoformat(),
            }

            return updated_budget

        except Exception as e:
            self.logger.error(f"Error en reconstrucción preserve_price: {e}")
            raise

    async def _reconstruct_adjust_proportionally(
        self, budget_id: str, changes: Dict[str, Any], impact: AnalysisResult
    ) -> Dict[str, Any]:
        """
        Reconstruir ajustando proporcionalmente.

        Esta estrategia distribuye los cambios proporcionalmente
        entre el costo y el margen.
        """
        try:
            # Obtener presupuesto original
            budget = await self.budget_manager.get_budget(budget_id)
            if not budget:
                raise ValueError(f"Presupuesto {budget_id} no encontrado")

            original_cost = Decimal(str(budget["cost"]))
            original_price = Decimal(str(budget["final_price"]))
            original_margin = (original_price - original_cost) / original_cost

            # Aplicar cambios al costo
            if "price" in changes:
                price_change = changes["price"]
                change_percentage = Decimal(str(price_change["percentage"])) / 100
                new_cost = original_cost * (1 + change_percentage)

                # Distribuir el impacto
                margin_impact = change_percentage * Decimal(
                    "0.4"
                )  # 40% del impacto al margen
                new_margin = original_margin * (1 - margin_impact)
            else:
                new_cost = original_cost
                new_margin = original_margin

            # Calcular nuevo precio
            new_price = new_cost * (1 + new_margin)

            # Actualizar presupuesto
            updated_budget = budget.copy()
            updated_budget["cost"] = float(new_cost)
            updated_budget["final_price"] = float(new_price)
            updated_budget["reconstruction_info"] = {
                "strategy": ReconstructionStrategy.ADJUST_PROPORTIONALLY,
                "original_margin": float(original_margin),
                "new_margin": float(new_margin),
                "timestamp": datetime.now().isoformat(),
            }

            return updated_budget

        except Exception as e:
            self.logger.error(f"Error en reconstrucción adjust_proportionally: {e}")
            raise

    async def _reconstruct_best_alternative(
        self, budget_id: str, changes: Dict[str, Any], impact: AnalysisResult
    ) -> Dict[str, Any]:
        """
        Reconstruir con mejor alternativa.

        Esta estrategia busca un paquete alternativo que mejor
        se ajuste a las características originales.
        """
        try:
            # Obtener presupuesto original
            budget = await self.budget_manager.get_budget(budget_id)
            if not budget:
                raise ValueError(f"Presupuesto {budget_id} no encontrado")

            # Buscar alternativas
            alternatives = await self.suggest_alternatives(budget_id, changes)
            if not alternatives:
                raise ValueError("No se encontraron alternativas viables")

            # Seleccionar mejor alternativa
            best_alternative = alternatives[0]  # Ya están ordenadas por similitud

            # Crear nuevo presupuesto con la alternativa
            updated_budget = budget.copy()
            updated_budget["package"] = best_alternative["package"]
            updated_budget["cost"] = best_alternative["package"]["cost"]
            updated_budget["final_price"] = best_alternative["package"]["price"]
            updated_budget["reconstruction_info"] = {
                "strategy": ReconstructionStrategy.BEST_ALTERNATIVE,
                "original_package_id": budget["package"]["id"],
                "similarity_score": best_alternative["similarity_score"],
                "timestamp": datetime.now().isoformat(),
            }

            return updated_budget

        except Exception as e:
            self.logger.error(f"Error en reconstrucción best_alternative: {e}")
            raise

    async def _cleanup_task(self):
        """Tarea periódica de limpieza."""
        while True:
            try:
                # Limpiar tareas completadas
                for budget_id, task in list(self._reconstruction_tasks.items()):
                    if task.done():
                        del self._reconstruction_tasks[budget_id]

                await asyncio.sleep(300)  # 5 minutos

            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)


# Instancia global
reconstruction_manager = BudgetReconstructionManager()


async def get_reconstruction_manager() -> BudgetReconstructionManager:
    """Obtener instancia única del gestor."""
    return reconstruction_manager
