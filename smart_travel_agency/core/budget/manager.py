"""
Gestor avanzado de presupuestos con optimización multi-pasada.

Este módulo implementa:
1. Gestión de presupuestos
2. Optimización iterativa
3. Análisis de mejoras
4. Registro de decisiones
"""

from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime
import asyncio
import logging
from dataclasses import dataclass

from prometheus_client import Counter, Histogram, Gauge

# Métricas
BUDGET_OPERATIONS = Counter(
    "budget_operations_total", "Number of budget operations", ["operation_type"]
)

OPTIMIZATION_IMPROVEMENTS = Histogram(
    "optimization_improvements_percentage",
    "Percentage improvements from optimization passes",
    ["pass_number"],
    buckets=[1, 2, 5, 10, 20, 50],
)

ACTIVE_OPTIMIZATIONS = Gauge(
    "active_optimizations_total", "Number of currently running optimization processes"
)


@dataclass
class OptimizationResult:
    """Resultado de una pasada de optimización."""

    pass_number: int
    original_price: Decimal
    optimized_price: Decimal
    improvement_percentage: float
    changes_applied: List[str]
    timestamp: datetime


@dataclass
class Budget:
    """Presupuesto con historial de optimización."""

    id: str
    customer_id: str
    vendor_id: str
    creation_date: datetime
    base_package: Dict[str, Any]
    current_price: Decimal
    optimization_history: List[OptimizationResult]
    status: str = "active"
    locked: bool = False


class BudgetManager:
    """
    Gestor de presupuestos con optimización multi-pasada.
    """

    def __init__(self):
        """Inicializar gestor."""
        self.active_budgets: Dict[str, Budget] = {}
        self.logger = logging.getLogger(__name__)
        self.optimization_threshold = Decimal("1.0")  # 1% mínimo de mejora

    async def create_budget(
        self, customer_id: str, vendor_id: str, package: Dict[str, Any]
    ) -> str:
        """
        Crear nuevo presupuesto.

        Args:
            customer_id: ID del cliente
            vendor_id: ID del vendedor
            package: Datos del paquete base

        Returns:
            ID del presupuesto creado
        """
        budget_id = f"budget_{customer_id}_{datetime.now().timestamp()}"

        budget = Budget(
            id=budget_id,
            customer_id=customer_id,
            vendor_id=vendor_id,
            creation_date=datetime.now(),
            base_package=package.copy(),
            current_price=Decimal(str(package["precio"])),
            optimization_history=[],
        )

        self.active_budgets[budget_id] = budget
        BUDGET_OPERATIONS.labels(operation_type="create").inc()

        self.logger.info(f"Created budget {budget_id} for customer {customer_id}")
        return budget_id

    async def optimize_budget(
        self, budget_id: str, max_passes: int = 3
    ) -> Tuple[bool, List[OptimizationResult]]:
        """
        Realizar optimización multi-pasada del presupuesto.

        Args:
            budget_id: ID del presupuesto
            max_passes: Máximo número de pasadas

        Returns:
            Tuple con éxito y lista de resultados
        """
        budget = self.active_budgets.get(budget_id)
        if not budget or budget.locked:
            return False, []

        ACTIVE_OPTIMIZATIONS.inc()
        try:
            current_price = budget.current_price
            results = []

            for pass_num in range(1, max_passes + 1):
                self.logger.info(
                    f"Starting optimization pass {pass_num} for budget {budget_id}"
                )

                # Realizar pasada de optimización
                optimized_data = await self._optimization_pass(
                    budget.base_package, pass_num
                )
                new_price = Decimal(str(optimized_data["precio"]))

                # Calcular mejora
                improvement = ((current_price - new_price) / current_price) * 100

                result = OptimizationResult(
                    pass_number=pass_num,
                    original_price=current_price,
                    optimized_price=new_price,
                    improvement_percentage=float(improvement),
                    changes_applied=self._get_changes(
                        budget.base_package, optimized_data
                    ),
                    timestamp=datetime.now(),
                )

                results.append(result)
                OPTIMIZATION_IMPROVEMENTS.labels(pass_number=pass_num).observe(
                    float(improvement)
                )

                # Verificar si la mejora es significativa
                if improvement > self.optimization_threshold:
                    current_price = new_price
                    budget.current_price = new_price
                    budget.base_package = optimized_data
                    self.logger.info(
                        f"Found improvement of {improvement:.2f}% in pass {pass_num}"
                    )
                else:
                    self.logger.info(f"No significant improvement in pass {pass_num}")
                    break

            budget.optimization_history.extend(results)
            BUDGET_OPERATIONS.labels(operation_type="optimize").inc()
            return True, results

        finally:
            ACTIVE_OPTIMIZATIONS.dec()

    async def _optimization_pass(
        self, package: Dict[str, Any], pass_number: int
    ) -> Dict[str, Any]:
        """
        Implementar lógica específica de optimización aquí.
        Esta es una versión básica que debe ser extendida.
        """
        # TODO: Implementar lógica real de optimización
        return package.copy()

    def _get_changes(
        self, old_data: Dict[str, Any], new_data: Dict[str, Any]
    ) -> List[str]:
        """Identificar cambios entre versiones de datos."""
        changes = []

        if old_data["precio"] != new_data["precio"]:
            changes.append(
                f"Cambio de precio: {old_data['precio']} -> {new_data['precio']}"
            )

        # Agregar más comparaciones según sea necesario

        return changes

    async def lock_budget(self, budget_id: str) -> bool:
        """
        Bloquear presupuesto para mantener estabilidad.

        Args:
            budget_id: ID del presupuesto

        Returns:
            True si se bloqueó correctamente
        """
        budget = self.active_budgets.get(budget_id)
        if not budget:
            return False

        budget.locked = True
        BUDGET_OPERATIONS.labels(operation_type="lock").inc()
        return True

    async def unlock_budget(self, budget_id: str) -> bool:
        """Desbloquear presupuesto."""
        budget = self.active_budgets.get(budget_id)
        if not budget:
            return False

        budget.locked = False
        BUDGET_OPERATIONS.labels(operation_type="unlock").inc()
        return True


# Instancia global del gestor
budget_manager = BudgetManager()


async def get_budget_manager() -> BudgetManager:
    """Obtener instancia única del gestor."""
    return budget_manager
