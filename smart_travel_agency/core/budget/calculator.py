"""
Calculador de presupuestos.

Este módulo implementa:
1. Cálculo dinámico de presupuestos
2. Gestión de costos y precios
3. Manejo de impuestos y cargos
4. Control de márgenes
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from decimal import Decimal
from prometheus_client import Counter, Histogram

from ..schemas import (
    Budget,
    TravelPackage,
    PriceComponent,
    MarginStrategy,
    TaxConfig,
    CalculationResult,
)
from ..metrics import get_metrics_collector
from ..memory import get_memory_manager

# Métricas
CALCULATION_OPERATIONS = Counter(
    "budget_calculation_operations_total",
    "Number of calculation operations",
    ["operation_type"],
)

CALCULATION_LATENCY = Histogram(
    "calculation_operation_latency_seconds",
    "Latency of calculation operations",
    ["operation_type"],
)


class BudgetCalculator:
    """
    Calculador de presupuestos.

    Responsabilidades:
    1. Calcular precios y costos
    2. Aplicar márgenes e impuestos
    3. Validar resultados
    """

    def __init__(self):
        """Inicializar calculador."""
        self.logger = logging.getLogger(__name__)
        self.memory = get_memory_manager()
        self.metrics = get_metrics_collector()

        # Configuración de cálculos
        self.config = {
            "default_margin": 0.20,  # 20% margen por defecto
            "min_margin": 0.10,  # 10% margen mínimo
            "max_margin": 0.40,  # 40% margen máximo
            "tax_rate": 0.21,  # 21% IVA
            "round_decimals": 2,  # Redondeo a 2 decimales
        }

        # Estrategias de margen
        self.margin_strategies = {
            MarginStrategy.FIXED: self._apply_fixed_margin,
            MarginStrategy.VARIABLE: self._apply_variable_margin,
            MarginStrategy.DYNAMIC: self._apply_dynamic_margin,
        }

    async def calculate_budget(
        self,
        packages: List[TravelPackage],
        margin_strategy: Optional[MarginStrategy] = None,
        tax_config: Optional[TaxConfig] = None,
        session_state: Optional[Dict[str, Any]] = None,
    ) -> CalculationResult:
        """
        Calcular presupuesto completo.

        Args:
            packages: Lista de paquetes a incluir
            margin_strategy: Estrategia de margen a aplicar
            tax_config: Configuración de impuestos
            session_state: Estado de sesión activa

        Returns:
            Resultado del cálculo
        """
        try:
            start_time = datetime.now()

            # Si hay sesión activa, usar datos aislados
            if session_state and session_state.get("is_active"):
                packages = await self._get_session_packages(packages, session_state)

            # Calcular componentes base
            base_components = await self._calculate_base_components(packages)

            # Aplicar estrategia de margen
            if not margin_strategy:
                margin_strategy = MarginStrategy.FIXED

            margin_components = await self.margin_strategies[margin_strategy](
                base_components
            )

            # Aplicar impuestos
            tax_components = await self._apply_taxes(margin_components, tax_config)

            # Calcular totales
            totals = self._calculate_totals(tax_components)

            # Validar resultados
            if not self._validate_calculation(totals):
                return CalculationResult(success=False, error="invalid_calculation")

            # Registrar métricas
            duration = (datetime.now() - start_time).total_seconds()
            CALCULATION_LATENCY.labels(operation_type="full_calculation").observe(
                duration
            )

            CALCULATION_OPERATIONS.labels(operation_type="full_calculation").inc()

            return CalculationResult(
                success=True,
                components=tax_components,
                totals=totals,
                metadata={
                    "margin_strategy": margin_strategy.value,
                    "tax_config": tax_config.dict() if tax_config else None,
                    "calculation_time": duration,
                },
            )

        except Exception as e:
            self.logger.error(f"Error en cálculo: {e}")
            return CalculationResult(success=False, error=str(e))

    async def _calculate_base_components(
        self, packages: List[TravelPackage]
    ) -> List[PriceComponent]:
        """Calcular componentes base del presupuesto."""
        try:
            components = []

            for package in packages:
                # Obtener costos actualizados
                costs = await self.memory.get_package_costs(package.id)

                # Crear componente base
                component = PriceComponent(
                    package_id=package.id,
                    description=package.description,
                    base_cost=costs["base_cost"],
                    additional_costs=costs.get("additional_costs", {}),
                    total_cost=sum(costs.get("additional_costs", {}).values())
                    + costs["base_cost"],
                )

                components.append(component)

            return components

        except Exception as e:
            self.logger.error(f"Error calculando componentes base: {e}")
            raise

    async def _apply_fixed_margin(
        self, components: List[PriceComponent]
    ) -> List[PriceComponent]:
        """Aplicar margen fijo a componentes."""
        try:
            margin = self.config["default_margin"]

            for component in components:
                # Aplicar margen fijo
                component.margin = margin
                component.price_before_tax = component.total_cost / (1 - margin)

                # Redondear
                component.price_before_tax = round(
                    component.price_before_tax, self.config["round_decimals"]
                )

            return components

        except Exception as e:
            self.logger.error(f"Error aplicando margen fijo: {e}")
            raise

    async def _apply_variable_margin(
        self, components: List[PriceComponent]
    ) -> List[PriceComponent]:
        """Aplicar margen variable según componente."""
        try:
            for component in components:
                # Obtener margen recomendado
                recommended = await self.memory.get_recommended_margin(
                    component.package_id
                )

                # Validar límites
                margin = max(
                    self.config["min_margin"],
                    min(recommended, self.config["max_margin"]),
                )

                # Aplicar margen
                component.margin = margin
                component.price_before_tax = component.total_cost / (1 - margin)

                # Redondear
                component.price_before_tax = round(
                    component.price_before_tax, self.config["round_decimals"]
                )

            return components

        except Exception as e:
            self.logger.error(f"Error aplicando margen variable: {e}")
            raise

    async def _apply_dynamic_margin(
        self, components: List[PriceComponent]
    ) -> List[PriceComponent]:
        """Aplicar margen dinámico basado en mercado."""
        try:
            for component in components:
                # Obtener datos de mercado
                market_data = await self.memory.get_market_data(component.package_id)

                # Calcular margen dinámico
                if market_data.get("high_demand"):
                    margin = min(
                        market_data["avg_margin"] * 1.2, self.config["max_margin"]
                    )
                else:
                    margin = max(
                        market_data["avg_margin"] * 0.9, self.config["min_margin"]
                    )

                # Aplicar margen
                component.margin = margin
                component.price_before_tax = component.total_cost / (1 - margin)

                # Redondear
                component.price_before_tax = round(
                    component.price_before_tax, self.config["round_decimals"]
                )

            return components

        except Exception as e:
            self.logger.error(f"Error aplicando margen dinámico: {e}")
            raise

    async def _apply_taxes(
        self, components: List[PriceComponent], tax_config: Optional[TaxConfig] = None
    ) -> List[PriceComponent]:
        """Aplicar impuestos a componentes."""
        try:
            # Usar configuración por defecto si no se especifica
            if not tax_config:
                tax_config = TaxConfig(rate=self.config["tax_rate"])

            for component in components:
                # Calcular impuestos
                component.tax_rate = tax_config.rate
                component.tax_amount = component.price_before_tax * component.tax_rate

                # Calcular precio final
                component.final_price = (
                    component.price_before_tax + component.tax_amount
                )

                # Redondear
                component.tax_amount = round(
                    component.tax_amount, self.config["round_decimals"]
                )
                component.final_price = round(
                    component.final_price, self.config["round_decimals"]
                )

            return components

        except Exception as e:
            self.logger.error(f"Error aplicando impuestos: {e}")
            raise

    def _calculate_totals(self, components: List[PriceComponent]) -> Dict[str, Decimal]:
        """Calcular totales del presupuesto."""
        try:
            totals = {
                "total_cost": sum(c.total_cost for c in components),
                "total_before_tax": sum(c.price_before_tax for c in components),
                "total_tax": sum(c.tax_amount for c in components),
                "final_total": sum(c.final_price for c in components),
            }

            # Redondear totales
            for key, value in totals.items():
                totals[key] = round(value, self.config["round_decimals"])

            return totals

        except Exception as e:
            self.logger.error(f"Error calculando totales: {e}")
            raise

    def _validate_calculation(self, totals: Dict[str, Decimal]) -> bool:
        """Validar resultados del cálculo."""
        try:
            # Validar valores positivos
            if any(v <= 0 for v in totals.values()):
                return False

            # Validar relaciones lógicas
            if not (
                totals["total_cost"]
                < totals["total_before_tax"]
                < totals["final_total"]
            ):
                return False

            # Validar margen efectivo
            effective_margin = (
                totals["total_before_tax"] - totals["total_cost"]
            ) / totals["total_before_tax"]

            if not (
                self.config["min_margin"]
                <= effective_margin
                <= self.config["max_margin"]
            ):
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error validando cálculo: {e}")
            return False

    async def _get_session_packages(
        self, packages: List[TravelPackage], session_state: Dict[str, Any]
    ) -> List[TravelPackage]:
        """Obtener paquetes con datos aislados de sesión."""
        try:
            # Obtener datos aislados
            isolated_data = await self.memory.get_session_data(session_state["id"])

            # Aplicar datos aislados
            for package in packages:
                if package.id in isolated_data:
                    package.update(isolated_data[package.id])

            return packages

        except Exception as e:
            self.logger.error(f"Error obteniendo datos de sesión: {e}")
            return packages


# Instancia global
budget_calculator = BudgetCalculator()


async def get_budget_calculator() -> BudgetCalculator:
    """Obtener instancia del calculador."""
    return budget_calculator
