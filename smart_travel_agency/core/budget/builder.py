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


class BuilderState(str, Enum):
    """Estados posibles del constructor de presupuestos."""

    INITIAL = "initial"
    COLLECTING_ITEMS = "collecting_items"
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

    def __init__(self, vendor_id: str):
        """
        Inicializa un nuevo constructor de presupuestos.
        
        Args:
            vendor_id: ID del vendedor
        """
        self.vendor_id = vendor_id
        self.items: List[BudgetItem] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self._suggestions: List[str] = []
        self.state = BuilderState.INITIAL
        self.metadata: Dict[str, Any] = {}
        
        # Obtener preferencias y provider manager
        pref_manager = get_preference_manager()
        self.preferences = pref_manager.get_vendor_preferences(vendor_id) if pref_manager else None
        self.provider_manager = get_provider_manager()

    def get_suggestions(self) -> List[str]:
        """
        Obtiene las sugerencias actuales para el presupuesto.
        
        Returns:
            Lista de sugerencias como strings
        """
        return self._suggestions

    def _generate_suggestions(self) -> List[str]:
        """Genera sugerencias basadas en el estado actual del presupuesto."""
        suggestions = []
        
        # Análisis de costos
        for item in self.items:
            if item.amount > Decimal('1000'):
                suggestions.append(f"💰 Hay una alternativa más económica para '{item.description}' que podría ahorrar hasta un 20%")
        
        # Análisis de temporada
        for item in self.items:
            if item.metadata.get('season') == 'high':
                suggestions.append(f"📅 El item '{item.description}' es más económico en temporada media. Cambiar la fecha podría ahorrar hasta 30%")
        
        # Análisis de paquetes
        provider_items = {}
        for item in self.items:
            provider = item.metadata.get('provider_id')
            if provider:
                if provider not in provider_items:
                    provider_items[provider] = []
                provider_items[provider].append(item)
        
        for provider, items in provider_items.items():
            if len(items) >= 2:
                descriptions = [item.description for item in items]
                suggestions.append(f"📦 Hay un paquete disponible que incluye: {', '.join(descriptions)}. Ahorro potencial del 15%")
        
        return suggestions

    def add_item(self, item: BudgetItem) -> None:
        """
        Agrega un item al presupuesto.
        
        Args:
            item: Item a agregar
        """
        # Validar el item
        if not self._validate_item(item):
            return
        
        # Validar contra preferencias del vendedor
        if self.preferences and "max_amount" in self.preferences:
            max_amount = Decimal(str(self.preferences["max_amount"]))
            if item.amount > max_amount:
                self.warnings.append(
                    f"El item {item.description} excede el monto máximo "
                    f"recomendado de {max_amount} {item.currency}"
                )
        
        # Agregar el item primero para que esté disponible para las sugerencias
        self.items.append(item)
        
        # Generar sugerencias
        new_suggestions = self._generate_suggestions()
        if new_suggestions:
            self._suggestions.extend(new_suggestions)
        
        self.state = BuilderState.COLLECTING_ITEMS

    def _validate_item(self, item: BudgetItem) -> bool:
        """
        Validar item según reglas de negocio y preferencias.
        
        Args:
            item: Item a validar
            
        Returns:
            True si el item es válido, False de lo contrario
        """
        errors = []
        warnings = []
        suggestions = []

        # Validaciones básicas
        if item.amount <= 0:
            errors.append(f"Monto inválido para {item.description}")

        if "provider_id" not in item.metadata:
            warnings.append(f"Item sin proveedor: {item.description}")

        # Validar contra preferencias
        if self.preferences:
            provider_id = item.metadata.get("provider_id")
            if provider_id in self.preferences.get("excluded_providers", []):
                errors.append(f"Proveedor excluido: {provider_id}")

            # Validar monto máximo
            total_amount = item.amount * item.quantity
            if (
                self.preferences.get("max_price")
                and total_amount > self.preferences["max_price"]
            ):
                warnings.append(
                    f"Monto total excede máximo preferido: {total_amount} > {self.preferences['max_price']}"
                )
                # Sugerir alternativas
                suggestions.append(
                    f"Buscar alternativas más económicas para: {item.description}"
                )

        # Propagar errores y advertencias
        self.errors.extend(errors)
        self.warnings.extend(warnings)
        self._suggestions.extend(suggestions)

        return len(errors) == 0

    def _apply_preferences_to_item(self, item: BudgetItem) -> BudgetItem:
        """
        Aplicar preferencias del vendedor al item.
        
        Args:
            item: Item a procesar
            
        Returns:
            Item procesado
        """
        # Aplicar reglas de precio
        for rule in self.preferences.get("price_rules", []):
            # TODO: Implementar evaluación de reglas
            pass

        return item

    def validate(self) -> ValidationResult:
        """
        Validar el presupuesto completo.
        
        Returns:
            Resultado de validación
        """
        self.state = BuilderState.CALCULATING
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
                total = sum(item.amount * item.quantity for item in self.items)
                if (
                    self.preferences.get("max_price")
                    and total > self.preferences["max_price"]
                ):
                    warnings.append(
                        f"Presupuesto total excede máximo: {total} > {self.preferences['max_price']}"
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

    def build(self) -> Budget:
        """
        Construir presupuesto final.
        
        Returns:
            Presupuesto construido
            
        Raises:
            ValueError: Si hay errores en la construcción
        """
        # No construir si hay errores
        if self.errors:
            raise ValueError("No se puede construir presupuesto con errores")

        # Validar estado final
        if not self.items:
            raise ValueError("No se puede construir presupuesto sin items")

        # Crear presupuesto
        budget = Budget(
            items=self.items.copy(),
            metadata=self.metadata.copy()
        )

        # Actualizar estado
        self.state = BuilderState.READY
        return budget


# Instancia global
budget_builder = BudgetBuilder("")


def get_budget_builder(vendor_id: str) -> BudgetBuilder:
    """
    Obtener una nueva instancia del builder.
    
    Args:
        vendor_id: ID del vendedor
        
    Returns:
        Nueva instancia del builder
    """
    return BudgetBuilder(vendor_id)
