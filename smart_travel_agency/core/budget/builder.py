"""
Sistema de construcción dinámica de presupuestos.

Este módulo implementa:
1. Construcción incremental de presupuestos
2. Validaciones en tiempo real
3. Integración con preferencias del vendedor
4. Control de estado del presupuesto
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from ..vendors.preferences import get_preference_manager, VendorPreferences
from ..providers.manager import get_provider_manager
from .models import Budget, BudgetItem, BudgetVersion
from .reconstruction import ReconstructionStrategy
from prometheus_client import Counter, Histogram

# Métricas
BUDGET_BUILD_OPERATIONS = Counter(
    "budget_build_operations_total",
    "Number of budget building operations",
    ["operation_type", "status"],
)

BUDGET_BUILD_LATENCY = Histogram(
    "budget_build_latency_seconds",
    "Latency of budget building operations",
    ["operation_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
)


class BuilderState(Enum):
    """Estados del builder de presupuestos."""

    INITIAL = "initial"
    COLLECTING_ITEMS = "collecting_items"
    VALIDATING = "validating"
    APPLYING_PREFERENCES = "applying_preferences"
    CALCULATING = "calculating"
    READY = "ready"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Resultado de validación."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]


class BudgetBuilder:
    """
    Builder para construcción dinámica de presupuestos.
    
    Implementa un patrón Builder con:
    1. Construcción incremental
    2. Validaciones en tiempo real
    3. Integración con preferencias
    4. Control de estado
    """

    def __init__(self, vendor_id: Optional[str] = None):
        """
        Inicializar builder.

        Args:
            vendor_id: ID del vendedor (opcional)
        """
        self.state = BuilderState.INITIAL
        self.vendor_id = vendor_id
        self.items: List[BudgetItem] = []
        self.currency: str = "USD"
        self.metadata: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
        # Obtener preferencias si hay vendor_id
        self.preferences = None
        if vendor_id:
            pref_manager = get_preference_manager()
            self.preferences = pref_manager.get_vendor_preferences(vendor_id)

        # Providers
        self.provider_manager = get_provider_manager()

    def with_currency(self, currency: str) -> "BudgetBuilder":
        """Establecer moneda."""
        self.currency = currency
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> "BudgetBuilder":
        """Agregar metadata."""
        self.metadata.update(metadata)
        return self

    def add_item(self, item: BudgetItem) -> "BudgetBuilder":
        """
        Agregar item al presupuesto.
        
        Args:
            item: Item a agregar
            
        Returns:
            Self para encadenamiento
        """
        with BUDGET_BUILD_LATENCY.labels("add_item").time():
            self.state = BuilderState.COLLECTING_ITEMS
            
            # Validar item
            validation = self._validate_item(item)
            if not validation.is_valid:
                self.errors.extend(validation.errors)
                self.warnings.extend(validation.warnings)
                BUDGET_BUILD_OPERATIONS.labels(
                    operation_type="add_item", status="error"
                ).inc()
                return self

            # Aplicar preferencias
            if self.preferences:
                item = self._apply_preferences_to_item(item)

            self.items.append(item)
            BUDGET_BUILD_OPERATIONS.labels(
                operation_type="add_item", status="success"
            ).inc()
            return self

    def _validate_item(self, item: BudgetItem) -> ValidationResult:
        """
        Validar item según reglas de negocio y preferencias.
        
        Args:
            item: Item a validar
            
        Returns:
            Resultado de validación
        """
        errors = []
        warnings = []
        suggestions = []

        # Validaciones básicas
        if item.price <= 0:
            errors.append(f"Precio inválido para {item.description}")

        if not item.provider_id:
            warnings.append(f"Item sin proveedor: {item.description}")

        # Validar contra preferencias
        if self.preferences:
            if item.provider_id in self.preferences.base.excluded_providers:
                errors.append(f"Proveedor excluido: {item.provider_id}")

            # Validar precio máximo
            if (
                self.preferences.base.max_price
                and item.price > self.preferences.base.max_price
            ):
                warnings.append(
                    f"Precio excede máximo preferido: {item.price} > {self.preferences.base.max_price}"
                )
                # Sugerir alternativas
                suggestions.append(
                    f"Buscar alternativas más económicas para: {item.description}"
                )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

    def _apply_preferences_to_item(self, item: BudgetItem) -> BudgetItem:
        """
        Aplicar preferencias del vendedor al item.
        
        Args:
            item: Item a procesar
            
        Returns:
            Item procesado
        """
        # Aplicar reglas de precio
        for rule in self.preferences.business_preferences.price_rules:
            # TODO: Implementar evaluación de reglas
            pass

        return item

    def validate(self) -> ValidationResult:
        """
        Validar el presupuesto completo.
        
        Returns:
            Resultado de validación
        """
        self.state = BuilderState.VALIDATING
        with BUDGET_BUILD_LATENCY.labels("validate").time():
            errors = []
            warnings = []
            suggestions = []

            # Validar items
            if not self.items:
                errors.append("Presupuesto sin items")

            # Validar consistencia
            currencies = set(item.currency for item in self.items)
            if len(currencies) > 1:
                warnings.append(f"Múltiples monedas en uso: {currencies}")
                suggestions.append("Considerar unificar monedas")

            # Validar contra preferencias
            if self.preferences:
                total = sum(item.price for item in self.items)
                if (
                    self.preferences.base.max_price
                    and total > self.preferences.base.max_price
                ):
                    warnings.append(
                        f"Presupuesto total excede máximo: {total} > {self.preferences.base.max_price}"
                    )

            result = ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions,
            )

            BUDGET_BUILD_OPERATIONS.labels(
                operation_type="validate",
                status="success" if result.is_valid else "error",
            ).inc()
            return result

    def build(self) -> Tuple[Optional[Budget], ValidationResult]:
        """
        Construir el presupuesto final.
        
        Returns:
            Tupla de (Presupuesto, Resultado de validación)
        """
        with BUDGET_BUILD_LATENCY.labels("build").time():
            # Validación final
            validation = self.validate()
            if not validation.is_valid:
                self.state = BuilderState.ERROR
                BUDGET_BUILD_OPERATIONS.labels(
                    operation_type="build", status="error"
                ).inc()
                return None, validation

            # Construir presupuesto
            self.state = BuilderState.CALCULATING
            budget = Budget(
                items=self.items.copy(),
                currency=self.currency,
                metadata=self.metadata.copy(),
            )

            self.state = BuilderState.READY
            BUDGET_BUILD_OPERATIONS.labels(
                operation_type="build", status="success"
            ).inc()
            return budget, validation


# Instancia global
budget_builder = BudgetBuilder()


def get_budget_builder(vendor_id: Optional[str] = None) -> BudgetBuilder:
    """
    Obtener una nueva instancia del builder.
    
    Args:
        vendor_id: ID del vendedor (opcional)
        
    Returns:
        Nueva instancia del builder
    """
    return BudgetBuilder(vendor_id)
