"""Tests para el sistema de validación de presupuestos."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from smart_travel_agency.core.budget.validator import (
    BudgetValidator,
    ValidationLevel,
    get_budget_validator,
)
from smart_travel_agency.core.budget.models import Budget, BudgetItem
from smart_travel_agency.core.vendors.preferences import (
    VendorPreferences,
    BasePreferences,
    BusinessPreferences,
    get_preference_manager,
)


@pytest.fixture
def sample_budget():
    """Fixture que crea un presupuesto de ejemplo."""
    return Budget(
        items=[
            BudgetItem(
                item_id=UUID("12345678-1234-5678-1234-567812345678"),
                provider_id="test_provider",
                description="Test Flight",
                price=Decimal("500.00"),
                currency="USD",
                quantity=1,
                type="flight",
            ),
            BudgetItem(
                item_id=UUID("22345678-1234-5678-1234-567812345678"),
                provider_id="test_provider",
                description="Test Hotel",
                price=Decimal("700.00"),
                currency="USD",
                quantity=1,
                type="accommodation",
            ),
        ],
        currency="USD",
    )


@pytest.fixture
def sample_preferences():
    """Fixture que crea preferencias de ejemplo."""
    base_prefs = BasePreferences(
        preferred_airlines=["TestAir"],
        min_rating=4.0,
        max_price=Decimal("2000.00"),
        excluded_providers=["bad_provider"],
    )

    business_prefs = BusinessPreferences(
        default_margin=Decimal("0.15"),
        min_margin=Decimal("0.05"),
        max_margin=Decimal("0.35"),
    )

    return VendorPreferences(
        vendor_id="test_vendor",
        name="Test Vendor",
        base=base_prefs,
        business_preferences=business_prefs,
    )


def test_validator_initialization():
    """Test de inicialización del validador."""
    validator = get_budget_validator()
    assert validator is not None
    assert len(validator.rules) > 0


def test_validate_valid_budget(sample_budget):
    """Test de validación de presupuesto válido."""
    validator = get_budget_validator()
    issues = validator.validate_budget(sample_budget)
    
    # No debería haber errores
    assert not any(issue.rule.level == ValidationLevel.ERROR for issue in issues)


def test_validate_mixed_currencies():
    """Test de validación con múltiples monedas."""
    budget = Budget(
        items=[
            BudgetItem(
                item_id=UUID("12345678-1234-5678-1234-567812345678"),
                provider_id="test_provider",
                description="USD Item",
                price=Decimal("100.00"),
                currency="USD",
                quantity=1,
                type="flight",
            ),
            BudgetItem(
                item_id=UUID("22345678-1234-5678-1234-567812345678"),
                provider_id="test_provider",
                description="EUR Item",
                price=Decimal("100.00"),
                currency="EUR",
                quantity=1,
                type="accommodation",
            ),
        ]
    )
    
    validator = get_budget_validator()
    issues = validator.validate_budget(budget)
    
    # Debe haber un error de moneda
    currency_issues = [
        issue for issue in issues
        if issue.rule.code == "VALID_CURRENCY"
    ]
    assert len(currency_issues) == 1
    assert currency_issues[0].rule.level == ValidationLevel.ERROR


def test_validate_invalid_amounts():
    """Test de validación con montos inválidos."""
    budget = Budget(
        items=[
            BudgetItem(
                item_id=UUID("12345678-1234-5678-1234-567812345678"),
                provider_id="test_provider",
                description="Invalid Item",
                price=Decimal("-100.00"),
                currency="USD",
                quantity=1,
                type="flight",
            ),
        ]
    )
    
    validator = get_budget_validator()
    issues = validator.validate_budget(budget)
    
    # Debe haber un error de monto
    amount_issues = [
        issue for issue in issues
        if issue.rule.code == "VALID_AMOUNTS"
    ]
    assert len(amount_issues) == 1
    assert amount_issues[0].rule.level == ValidationLevel.ERROR


def test_validate_incomplete_package():
    """Test de validación de paquete incompleto."""
    budget = Budget(
        items=[
            BudgetItem(
                item_id=UUID("12345678-1234-5678-1234-567812345678"),
                provider_id="test_provider",
                description="Only Flight",
                price=Decimal("500.00"),
                currency="USD",
                quantity=1,
                type="flight",
            ),
        ]
    )
    
    validator = get_budget_validator()
    issues = validator.validate_budget(budget)
    
    # Debe haber una advertencia de composición
    composition_issues = [
        issue for issue in issues
        if issue.rule.code == "COMPLETE_PACKAGE"
    ]
    assert len(composition_issues) == 1
    assert composition_issues[0].rule.level == ValidationLevel.WARNING


def test_validate_vendor_preferences(sample_budget, sample_preferences):
    """Test de validación con preferencias de vendedor."""
    # Registrar preferencias
    pref_manager = get_preference_manager()
    pref_manager.update_vendor_preferences(sample_preferences)
    
    # Agregar item con proveedor excluido
    sample_budget.items.append(
        BudgetItem(
            item_id=UUID("32345678-1234-5678-1234-567812345678"),
            provider_id="bad_provider",
            description="Bad Provider Item",
            price=Decimal("100.00"),
            currency="USD",
            quantity=1,
            type="activity",
        )
    )
    
    validator = get_budget_validator()
    issues = validator.validate_budget(sample_budget, "test_vendor")
    
    # Debe haber una advertencia de proveedor excluido
    preference_issues = [
        issue for issue in issues
        if issue.rule.code == "VENDOR_PREFERENCES"
    ]
    assert len(preference_issues) == 1
    assert preference_issues[0].rule.level == ValidationLevel.WARNING


def test_validate_vendor_limits(sample_budget, sample_preferences):
    """Test de validación de límites del vendedor."""
    # Registrar preferencias
    pref_manager = get_preference_manager()
    pref_manager.update_vendor_preferences(sample_preferences)
    
    # Agregar item que excede límite
    sample_budget.items.append(
        BudgetItem(
            item_id=UUID("32345678-1234-5678-1234-567812345678"),
            provider_id="test_provider",
            description="Expensive Item",
            price=Decimal("1000.00"),
            currency="USD",
            quantity=1,
            type="activity",
        )
    )
    
    validator = get_budget_validator()
    issues = validator.validate_budget(sample_budget, "test_vendor")
    
    # Debe haber un error de límite excedido
    limit_issues = [
        issue for issue in issues
        if issue.rule.code == "VENDOR_LIMITS"
    ]
    assert len(limit_issues) == 1
    assert limit_issues[0].rule.level == ValidationLevel.ERROR
