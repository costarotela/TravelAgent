"""Tests for budget rules."""

import pytest
from src.core.budget.rules import BudgetRules
from src.core.models.travel import TravelPackage


def test_apply_margin():
    """Test margin application."""
    rules = BudgetRules()

    # Test regular margin
    assert rules.apply_margin(100.0, "regular") == 115.0

    # Test corporate margin
    assert rules.apply_margin(100.0, "corporate") == 110.0

    # Test VIP margin
    assert rules.apply_margin(100.0, "vip") == 120.0

    # Test default margin
    assert rules.apply_margin(100.0, "unknown") == 115.0


def test_check_availability():
    """Test availability check."""
    rules = BudgetRules()

    # Test package with availability
    package = TravelPackage(availability=True)
    assert rules.check_availability(package) is True

    # Test package without availability
    package = TravelPackage(availability=False)
    assert rules.check_availability(package) is False

    # Test package without availability attribute
    package = TravelPackage()
    assert rules.check_availability(package) is True


def test_validate_budget_items():
    """Test budget item validation."""
    rules = BudgetRules()

    # Test valid items
    valid_items = {
        "flight": {"price": 100.0, "date": "2024-03-01", "provider": "TestAir"}
    }
    assert rules.validate_budget_items(valid_items) == {}

    # Test invalid items
    invalid_items = {
        "hotel": {"price": 0, "provider": "TestHotel"}  # Invalid price  # Missing date
    }
    errors = rules.validate_budget_items(invalid_items)
    assert "hotel" in errors
    assert "Precio debe ser mayor a 0" in errors["hotel"]
