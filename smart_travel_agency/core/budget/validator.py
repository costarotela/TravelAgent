"""
Sistema de validación crítica de presupuestos.

Este módulo implementa:
1. Validaciones críticas de negocio
2. Reglas de composición de presupuestos
3. Validaciones de integridad de datos
4. Verificación de restricciones del vendedor
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from uuid import UUID

from prometheus_client import Counter, Histogram

from ..vendors.preferences import get_preference_manager, VendorPreferences
from ..providers.manager import get_provider_manager
from .models import Budget, BudgetItem

# Métricas
VALIDATION_OPERATIONS = Counter(
    "budget_validation_operations_total",
    "Number of budget validation operations",
    ["validation_type", "result"],
)

VALIDATION_LATENCY = Histogram(
    "budget_validation_latency_seconds",
    "Latency of budget validation operations",
    ["validation_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
)


class ValidationLevel(Enum):
    """Niveles de validación."""

    ERROR = "error"  # Debe ser corregido
    WARNING = "warning"  # Puede proceder pero requiere atención
    INFO = "info"  # Informativo solamente


@dataclass
class ValidationRule:
    """Regla de validación."""

    code: str
    description: str
    level: ValidationLevel
    category: str
    enabled: bool = True


@dataclass
class ValidationIssue:
    """Problema de validación identificado."""

    rule: ValidationRule
    message: str
    affected_items: List[UUID] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class BudgetValidator:
    """
    Validador avanzado de presupuestos.

    Implementa validaciones críticas para asegurar:
    1. Integridad de datos
    2. Reglas de negocio
    3. Restricciones del vendedor
    4. Composición válida
    """

    def __init__(self):
        """Inicializar validador."""
        self._load_validation_rules()
        self.provider_manager = get_provider_manager()
        self.preference_manager = get_preference_manager()

    def _load_validation_rules(self):
        """Cargar reglas de validación."""
        self.rules: Dict[str, ValidationRule] = {
            # Reglas de integridad
            "VALID_CURRENCY": ValidationRule(
                code="VALID_CURRENCY",
                description="Moneda válida y consistente",
                level=ValidationLevel.ERROR,
                category="integrity",
            ),
            "VALID_AMOUNTS": ValidationRule(
                code="VALID_AMOUNTS",
                description="Montos válidos y positivos",
                level=ValidationLevel.ERROR,
                category="integrity",
            ),
            "VALID_DATES": ValidationRule(
                code="VALID_DATES",
                description="Fechas válidas y coherentes",
                level=ValidationLevel.ERROR,
                category="integrity",
            ),
            
            # Reglas de negocio
            "MARGIN_LIMITS": ValidationRule(
                code="MARGIN_LIMITS",
                description="Márgenes dentro de límites permitidos",
                level=ValidationLevel.ERROR,
                category="business",
            ),
            "PRICE_LIMITS": ValidationRule(
                code="PRICE_LIMITS",
                description="Precios dentro de límites permitidos",
                level=ValidationLevel.WARNING,
                category="business",
            ),
            "PROVIDER_STATUS": ValidationRule(
                code="PROVIDER_STATUS",
                description="Proveedores activos y válidos",
                level=ValidationLevel.ERROR,
                category="business",
            ),
            
            # Reglas de composición
            "COMPLETE_PACKAGE": ValidationRule(
                code="COMPLETE_PACKAGE",
                description="Paquete con componentes necesarios",
                level=ValidationLevel.WARNING,
                category="composition",
            ),
            "VALID_COMBINATIONS": ValidationRule(
                code="VALID_COMBINATIONS",
                description="Combinaciones válidas de servicios",
                level=ValidationLevel.WARNING,
                category="composition",
            ),
            
            # Reglas de vendedor
            "VENDOR_PREFERENCES": ValidationRule(
                code="VENDOR_PREFERENCES",
                description="Cumple preferencias del vendedor",
                level=ValidationLevel.WARNING,
                category="vendor",
            ),
            "VENDOR_LIMITS": ValidationRule(
                code="VENDOR_LIMITS",
                description="Dentro de límites del vendedor",
                level=ValidationLevel.ERROR,
                category="vendor",
            ),
        }

    def validate_budget(
        self, budget: Budget, vendor_id: Optional[str] = None
    ) -> List[ValidationIssue]:
        """
        Validar presupuesto completo.
        
        Args:
            budget: Presupuesto a validar
            vendor_id: ID del vendedor (opcional)
            
        Returns:
            Lista de problemas encontrados
        """
        with VALIDATION_LATENCY.labels("full_validation").time():
            issues: List[ValidationIssue] = []
            
            # Obtener preferencias si hay vendor_id
            vendor_preferences = None
            if vendor_id:
                vendor_preferences = self.preference_manager.get_vendor_preferences(vendor_id)

            # Validar integridad
            issues.extend(self._validate_integrity(budget))
            
            # Validar reglas de negocio
            issues.extend(self._validate_business_rules(budget))
            
            # Validar composición
            issues.extend(self._validate_composition(budget))
            
            # Validar preferencias de vendedor
            if vendor_preferences:
                issues.extend(
                    self._validate_vendor_rules(budget, vendor_preferences)
                )

            # Registrar métricas
            self._record_validation_metrics(issues)
            
            return issues

    def _validate_integrity(self, budget: Budget) -> List[ValidationIssue]:
        """Validar integridad de datos."""
        issues = []
        
        # Validar moneda
        currencies = {item.currency for item in budget.items}
        if len(currencies) > 1:
            issues.append(
                ValidationIssue(
                    rule=self.rules["VALID_CURRENCY"],
                    message=f"Múltiples monedas en uso: {currencies}",
                    context={"currencies": list(currencies)},
                )
            )
        
        # Validar montos
        for item in budget.items:
            if item.price <= 0:
                issues.append(
                    ValidationIssue(
                        rule=self.rules["VALID_AMOUNTS"],
                        message=f"Monto inválido en item: {item.description}",
                        affected_items=[item.item_id],
                        context={"price": str(item.price)},
                    )
                )
        
        return issues

    def _validate_business_rules(self, budget: Budget) -> List[ValidationIssue]:
        """Validar reglas de negocio."""
        issues = []
        
        # Validar márgenes
        total_cost = sum(item.price for item in budget.items)
        if total_cost > 0:
            margin = (budget.total_amount() - total_cost) / total_cost
            if margin < Decimal("0.05") or margin > Decimal("0.35"):
                issues.append(
                    ValidationIssue(
                        rule=self.rules["MARGIN_LIMITS"],
                        message=f"Margen fuera de límites: {margin:.2%}",
                        context={"margin": float(margin)},
                    )
                )
        
        # Validar proveedores
        provider_ids = {item.provider_id for item in budget.items}
        for provider_id in provider_ids:
            if not self.provider_manager.is_provider_active(provider_id):
                affected_items = [
                    item.item_id
                    for item in budget.items
                    if item.provider_id == provider_id
                ]
                issues.append(
                    ValidationIssue(
                        rule=self.rules["PROVIDER_STATUS"],
                        message=f"Proveedor inactivo: {provider_id}",
                        affected_items=affected_items,
                        context={"provider_id": provider_id},
                    )
                )
        
        return issues

    def _validate_composition(self, budget: Budget) -> List[ValidationIssue]:
        """Validar composición del presupuesto."""
        issues = []
        
        # Verificar componentes necesarios
        components = {item.type for item in budget.items}
        required = {"flight", "accommodation"}
        missing = required - components
        if missing:
            issues.append(
                ValidationIssue(
                    rule=self.rules["COMPLETE_PACKAGE"],
                    message=f"Faltan componentes necesarios: {missing}",
                    context={"missing": list(missing)},
                )
            )
        
        return issues

    def _validate_vendor_rules(
        self, budget: Budget, preferences: VendorPreferences
    ) -> List[ValidationIssue]:
        """Validar reglas específicas del vendedor."""
        issues = []
        
        # Validar límites de precio
        if preferences.base.max_price:
            total = budget.total_amount()
            if total > preferences.base.max_price:
                issues.append(
                    ValidationIssue(
                        rule=self.rules["VENDOR_LIMITS"],
                        message=(
                            f"Presupuesto excede límite del vendedor: "
                            f"{total} > {preferences.base.max_price}"
                        ),
                        context={
                            "total": str(total),
                            "limit": str(preferences.base.max_price),
                        },
                    )
                )
        
        # Validar proveedores excluidos
        for item in budget.items:
            if item.provider_id in preferences.base.excluded_providers:
                issues.append(
                    ValidationIssue(
                        rule=self.rules["VENDOR_PREFERENCES"],
                        message=f"Proveedor excluido: {item.provider_id}",
                        affected_items=[item.item_id],
                        context={"provider_id": item.provider_id},
                    )
                )
        
        return issues

    def _record_validation_metrics(self, issues: List[ValidationIssue]):
        """Registrar métricas de validación."""
        for issue in issues:
            VALIDATION_OPERATIONS.labels(
                validation_type=issue.rule.category,
                result=issue.rule.level.value,
            ).inc()


# Instancia global
budget_validator = BudgetValidator()


def get_budget_validator() -> BudgetValidator:
    """
    Obtener instancia del validador.
    
    Returns:
        Instancia única del validador
    """
    return budget_validator
