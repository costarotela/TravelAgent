"""Tests para el sistema de construcción de presupuestos."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from smart_travel_agency.core.budget.builder import (
    BudgetBuilder,
    BuilderState,
    get_budget_builder,
)
from smart_travel_agency.core.budget.models import BudgetItem
from smart_travel_agency.core.vendors.preferences import (
    VendorPreferences,
    BasePreferences,
    BusinessPreferences,
    get_preference_manager,
)


@pytest.fixture
def sample_item():
    """Fixture que crea un item de ejemplo."""
    return BudgetItem(
        item_id=UUID("12345678-1234-5678-1234-567812345678"),
        provider_id="test_provider",
        description="Test Item",
        price=Decimal("100.00"),
        currency="USD",
        quantity=1,
    )


@pytest.fixture
def sample_preferences():
    """Fixture que crea preferencias de ejemplo."""
    base_prefs = BasePreferences(
        preferred_airlines=["TestAir"],
        min_rating=4.0,
        max_price=Decimal("1000.00"),
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


def test_builder_initialization():
    """Test de inicialización del builder."""
    builder = get_budget_builder()
    assert builder.state == BuilderState.INITIAL
    assert builder.currency == "USD"
    assert len(builder.items) == 0


def test_builder_with_vendor(sample_preferences):
    """Test del builder con preferencias de vendedor."""
    # Registrar preferencias
    pref_manager = get_preference_manager()
    pref_manager.update_vendor_preferences(sample_preferences)

    # Crear builder con vendor_id
    builder = get_budget_builder("test_vendor")
    assert builder.vendor_id == "test_vendor"
    assert builder.preferences is not None
    assert builder.preferences.vendor_id == "test_vendor"


def test_add_valid_item(sample_item):
    """Test de agregado de item válido."""
    builder = get_budget_builder()
    builder.add_item(sample_item)
    
    assert len(builder.items) == 1
    assert builder.state == BuilderState.COLLECTING_ITEMS
    assert len(builder.errors) == 0


def test_add_invalid_item():
    """Test de agregado de item inválido."""
    invalid_item = BudgetItem(
        item_id=UUID("12345678-1234-5678-1234-567812345678"),
        provider_id="test_provider",
        description="Invalid Item",
        price=Decimal("-100.00"),  # Precio inválido
        currency="USD",
        quantity=1,
    )

    builder = get_budget_builder()
    builder.add_item(invalid_item)
    
    assert len(builder.items) == 0
    assert len(builder.errors) > 0


def test_validate_empty_budget():
    """Test de validación de presupuesto vacío."""
    builder = get_budget_builder()
    validation = builder.validate()
    
    assert not validation.is_valid
    assert len(validation.errors) > 0
    assert "Presupuesto sin items" in validation.errors


def test_validate_mixed_currencies(sample_item):
    """Test de validación con múltiples monedas."""
    builder = get_budget_builder()
    
    # Agregar item en USD
    builder.add_item(sample_item)
    
    # Agregar item en EUR
    eur_item = BudgetItem(
        item_id=UUID("22345678-1234-5678-1234-567812345678"),
        provider_id="test_provider",
        description="EUR Item",
        price=Decimal("100.00"),
        currency="EUR",
        quantity=1,
    )
    builder.add_item(eur_item)
    
    validation = builder.validate()
    assert validation.is_valid  # No es error, solo warning
    assert len(validation.warnings) > 0
    assert any("monedas" in w for w in validation.warnings)


def test_build_valid_budget(sample_item):
    """Test de construcción de presupuesto válido."""
    builder = get_budget_builder()
    builder.add_item(sample_item)
    
    budget, validation = builder.build()
    
    assert budget is not None
    assert validation.is_valid
    assert len(budget.items) == 1
    assert builder.state == BuilderState.READY


def test_build_invalid_budget():
    """Test de construcción de presupuesto inválido."""
    builder = get_budget_builder()
    budget, validation = builder.build()
    
    assert budget is None
    assert not validation.is_valid
    assert builder.state == BuilderState.ERROR


def test_preferences_validation(sample_item, sample_preferences):
    """Test de validación con preferencias."""
    # Registrar preferencias
    pref_manager = get_preference_manager()
    pref_manager.update_vendor_preferences(sample_preferences)

    # Crear item que excede precio máximo
    expensive_item = BudgetItem(
        item_id=UUID("32345678-1234-5678-1234-567812345678"),
        provider_id="test_provider",
        description="Expensive Item",
        price=Decimal("2000.00"),  # Excede max_price en preferencias
        currency="USD",
        quantity=1,
    )

    builder = get_budget_builder("test_vendor")
    builder.add_item(expensive_item)
    
    validation = builder.validate()
    assert validation.is_valid  # No es error, solo warning
    assert len(validation.warnings) > 0
    assert any("excede máximo" in w for w in validation.warnings)


def test_excluded_provider_validation(sample_preferences):
    """Test de validación de proveedor excluido."""
    # Registrar preferencias
    pref_manager = get_preference_manager()
    pref_manager.update_vendor_preferences(sample_preferences)

    # Crear item con proveedor excluido
    bad_item = BudgetItem(
        item_id=UUID("42345678-1234-5678-1234-567812345678"),
        provider_id="bad_provider",  # Proveedor excluido en preferencias
        description="Bad Provider Item",
        price=Decimal("100.00"),
        currency="USD",
        quantity=1,
    )

    builder = get_budget_builder("test_vendor")
    builder.add_item(bad_item)
    
    assert len(builder.errors) > 0
    assert any("Proveedor excluido" in e for e in builder.errors)
