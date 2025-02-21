"""
Tests para el sistema de construcción de presupuestos.

Verifica:
1. Construcción incremental de presupuestos
2. Validaciones en tiempo real
3. Integración con preferencias
4. Control de estado
5. Manejo de errores y advertencias
"""

import pytest
from unittest.mock import Mock, patch
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any
from uuid import UUID

from smart_travel_agency.core.budget.builder import (
    BudgetBuilder,
    BuilderState,
    ValidationResult,
    get_budget_builder
)
from smart_travel_agency.core.budget.models import BudgetItem, Budget

# Fixtures
@pytest.fixture
def basic_item() -> BudgetItem:
    """Item básico válido para pruebas."""
    return BudgetItem(
        description="Hotel Test",
        amount=Decimal("100.00"),
        quantity=2,
        currency="USD",
        metadata={"provider_id": "test_provider", "category": "accommodation"}
    )

@pytest.fixture
def mock_preferences():
    """Mock de preferencias del vendedor."""
    return {
        "max_amount": Decimal("500.00"),
        "excluded_providers": ["excluded_provider"],
        "price_rules": []
    }

@pytest.fixture
def mock_preference_manager(mock_preferences):
    """Mock del gestor de preferencias."""
    manager = Mock()
    manager.get_vendor_preferences.return_value = mock_preferences
    return manager

@pytest.fixture
def mock_provider_manager():
    """Mock del gestor de proveedores."""
    manager = Mock()
    manager.search_alternatives.return_value = [
        BudgetItem(
            description="Hotel Económico",
            amount=Decimal("80.00"),
            quantity=1,
            currency="USD",
            metadata={
                "provider_id": "test_provider",
                "category": "accommodation",
                "rating": 3
            }
        ),
        BudgetItem(
            description="Hotel Premium",
            amount=Decimal("150.00"),
            quantity=1,
            currency="USD",
            metadata={
                "provider_id": "test_provider",
                "category": "accommodation",
                "rating": 5
            }
        )
    ]
    return manager

class TestBudgetBuilder:
    """Suite de pruebas para el BudgetBuilder."""

    def test_initial_state(self, mock_preferences, mock_preference_manager):
        """Verificar estado inicial del builder."""
        with patch("smart_travel_agency.core.budget.builder.get_preference_manager") as mock_get_prefs:
            mock_get_prefs.return_value = mock_preference_manager
            builder = BudgetBuilder(vendor_id="test_vendor")
            assert builder.state == BuilderState.INITIAL
            assert len(builder.items) == 0
            assert len(builder.errors) == 0
            assert len(builder.warnings) == 0

    def test_add_valid_item(self, mock_preferences, mock_preference_manager):
        """Verificar agregar item válido."""
        with patch("smart_travel_agency.core.budget.builder.get_preference_manager") as mock_get_prefs:
            mock_get_prefs.return_value = mock_preference_manager
            
            builder = BudgetBuilder(vendor_id="test_vendor")
            basic_item = BudgetItem(
                description="Hotel Standard",
                amount=Decimal("100.00"),
                quantity=1,
                currency="USD",
                metadata={"provider_id": "test_provider"}
            )
            
            builder.add_item(basic_item)
            assert len(builder.items) == 1
            assert len(builder.errors) == 0

    def test_add_invalid_item(self, mock_preferences, mock_preference_manager):
        """Verificar rechazo de item inválido."""
        with patch("smart_travel_agency.core.budget.builder.get_preference_manager") as mock_get_prefs:
            mock_get_prefs.return_value = mock_preference_manager
            
            builder = BudgetBuilder(vendor_id="test_vendor")
            invalid_item = BudgetItem(
                description="Invalid Item",
                amount=Decimal("-50.00"),
                quantity=1,
                currency="USD",
                metadata={"provider_id": "test_provider"}
            )
            
            builder.add_item(invalid_item)
            assert len(builder.items) == 0
            assert len(builder.errors) > 0

    def test_vendor_preferences_validation(self, mock_preferences, mock_provider_manager):
        """Verificar que se validan las preferencias del vendedor."""
        with patch("smart_travel_agency.core.budget.builder.get_preference_manager") as mock_get_prefs, \
             patch("smart_travel_agency.core.budget.builder.get_provider_manager") as mock_get_provider:
            
            mock_get_prefs.return_value = Mock()
            mock_get_prefs.return_value.get_vendor_preferences.return_value = mock_preferences
            mock_get_provider.return_value = mock_provider_manager
            
            builder = BudgetBuilder(vendor_id="test_vendor")
            
            # Item que excede el monto máximo
            expensive_item = BudgetItem(
                description="Hotel Lujo",
                amount=Decimal("600.00"),
                quantity=1,
                currency="USD",
                metadata={
                    "provider_id": "test_provider",
                    "category": "accommodation",
                    "rating": 5
                }
            )
            
            builder.add_item(expensive_item)
            
            # Verificar que se generó una advertencia
            assert len(builder.warnings) >= 1
            assert any("excede" in w.lower() for w in builder.warnings)
            
            # Verificar que se generaron sugerencias
            suggestions = builder.get_suggestions()
            assert len(suggestions) >= 1
            assert any("alternativ" in s.lower() for s in suggestions)

    def test_excluded_provider_validation(self, mock_preferences, mock_preference_manager):
        """Verificar validación de proveedores excluidos."""
        with patch("smart_travel_agency.core.budget.builder.get_preference_manager") as mock_get_prefs:
            mock_get_prefs.return_value = mock_preference_manager
            
            builder = BudgetBuilder(vendor_id="test_vendor")
            excluded_item = BudgetItem(
                description="Hotel Excluido",
                amount=Decimal("100.00"),
                quantity=1,
                currency="USD",
                metadata={"provider_id": "excluded_provider"}
            )
            
            builder.add_item(excluded_item)
            assert len(builder.errors) > 0
            assert len(builder.items) == 0

    def test_build_complete_budget(self, mock_preferences, mock_preference_manager):
        """Verificar construcción completa del presupuesto."""
        with patch("smart_travel_agency.core.budget.builder.get_preference_manager") as mock_get_prefs:
            mock_get_prefs.return_value = mock_preference_manager
            
            builder = BudgetBuilder(vendor_id="test_vendor")
            basic_item = BudgetItem(
                description="Hotel Standard",
                amount=Decimal("100.00"),
                quantity=1,
                currency="USD",
                metadata={"provider_id": "test_provider"}
            )
            
            builder.add_item(basic_item)
            budget = builder.build()
            assert len(budget.items) == 1
            assert budget.items[0].amount == Decimal("100.00")

    def test_build_with_errors(self, mock_preferences, mock_preference_manager):
        """Verificar que no se puede construir con errores."""
        with patch("smart_travel_agency.core.budget.builder.get_preference_manager") as mock_get_prefs:
            mock_get_prefs.return_value = mock_preference_manager
            
            builder = BudgetBuilder(vendor_id="test_vendor")
            invalid_item = BudgetItem(
                description="Invalid Item",
                amount=Decimal("-50.00"),
                quantity=1,
                currency="USD",
                metadata={"provider_id": "test_provider"}
            )
            
            builder.add_item(invalid_item)
            with pytest.raises(ValueError):
                builder.build()

    def test_state_transitions(self, mock_preferences, mock_preference_manager):
        """Verificar transiciones de estado correctas."""
        with patch("smart_travel_agency.core.budget.builder.get_preference_manager") as mock_get_prefs:
            mock_get_prefs.return_value = mock_preference_manager
            
            builder = BudgetBuilder(vendor_id="test_vendor")
            assert builder.state == BuilderState.INITIAL
            
            basic_item = BudgetItem(
                description="Hotel Standard",
                amount=Decimal("100.00"),
                quantity=1,
                currency="USD",
                metadata={"provider_id": "test_provider"}
            )
            
            builder.add_item(basic_item)
            assert builder.state == BuilderState.COLLECTING_ITEMS
            
            budget = builder.build()
            assert builder.state == BuilderState.READY

class TestBudgetBuilderSuggestions:
    """Suite de pruebas para el sistema de sugerencias del BudgetBuilder."""

    def test_suggestions_for_expensive_item(self, mock_preferences, mock_provider_manager):
        """Verificar sugerencias para items que exceden el presupuesto."""
        with patch("smart_travel_agency.core.budget.builder.get_preference_manager") as mock_get_prefs, \
             patch("smart_travel_agency.core.budget.builder.get_provider_manager") as mock_get_provider:
            
            mock_get_prefs.return_value = Mock()
            mock_get_prefs.return_value.get_vendor_preferences.return_value = mock_preferences
            mock_get_provider.return_value = mock_provider_manager
            
            expensive_item = BudgetItem(
                description="Hotel Lujo",
                amount=Decimal("600.00"),
                quantity=1,
                currency="USD",
                metadata={
                    "provider_id": "test_provider",
                    "category": "accommodation",
                    "rating": 5
                }
            )
            
            builder = BudgetBuilder(vendor_id="test_vendor")
            builder.add_item(expensive_item)
            
            # Verificar que se generaron sugerencias
            assert len(builder.get_suggestions()) >= 2
            # Verificar que las sugerencias incluyen alternativas más económicas
            assert any("económic" in s.lower() for s in builder.get_suggestions())
            # Verificar que se mantiene la calidad del servicio
            assert any("premium" in s.lower() for s in builder.get_suggestions())

    def test_suggestions_for_seasonal_pricing(self, mock_preferences, mock_provider_manager):
        """Verificar sugerencias basadas en precios estacionales."""
        with patch("smart_travel_agency.core.budget.builder.get_preference_manager") as mock_get_prefs, \
             patch("smart_travel_agency.core.budget.builder.get_provider_manager") as mock_get_provider:
            
            mock_get_prefs.return_value = Mock()
            mock_get_prefs.return_value.get_vendor_preferences.return_value = mock_preferences
            mock_get_provider.return_value = mock_provider_manager
            
            # Simular item en temporada alta
            seasonal_item = BudgetItem(
                description="Hotel Playa",
                amount=Decimal("200.00"),
                quantity=1,
                currency="USD",
                metadata={
                    "provider_id": "test_provider",
                    "category": "accommodation",
                    "season": "high",
                    "location": "beach"
                }
            )
            
            builder = BudgetBuilder(vendor_id="test_vendor")
            builder.add_item(seasonal_item)
            
            suggestions = builder.get_suggestions()
            # Verificar sugerencias de temporada
            assert any("temporada baja" in s.lower() for s in suggestions)
            # Verificar sugerencias de alternativas
            assert any("alternativ" in s.lower() for s in suggestions)

    def test_suggestions_for_package_optimization(self, mock_preferences, mock_provider_manager):
        """Verificar sugerencias para optimización de paquetes."""
        with patch("smart_travel_agency.core.budget.builder.get_preference_manager") as mock_get_prefs, \
             patch("smart_travel_agency.core.budget.builder.get_provider_manager") as mock_get_provider:
            
            mock_get_prefs.return_value = Mock()
            mock_get_prefs.return_value.get_vendor_preferences.return_value = mock_preferences
            mock_get_provider.return_value = mock_provider_manager
            
            # Agregar múltiples items del mismo proveedor
            builder = BudgetBuilder(vendor_id="test_vendor")
            items = [
                BudgetItem(
                    description="Hotel Standard",
                    amount=Decimal("100.00"),
                    quantity=1,
                    currency="USD",
                    metadata={
                        "provider_id": "test_provider",
                        "category": "accommodation"
                    }
                ),
                BudgetItem(
                    description="Excursión Ciudad",
                    amount=Decimal("50.00"),
                    quantity=2,
                    currency="USD",
                    metadata={
                        "provider_id": "test_provider",
                        "category": "activity"
                    }
                )
            ]
            
            for item in items:
                builder.add_item(item)
            
            suggestions = builder.get_suggestions()
            # Verificar sugerencias de paquetes
            assert any("paquete" in s.lower() or "mejor precio" in s.lower() for s in suggestions)

    def test_no_suggestions_for_optimal_items(self, mock_preferences, mock_provider_manager):
        """Verificar que no se generan sugerencias innecesarias."""
        with patch("smart_travel_agency.core.budget.builder.get_preference_manager") as mock_get_prefs, \
             patch("smart_travel_agency.core.budget.builder.get_provider_manager") as mock_get_provider:
            
            mock_get_prefs.return_value = Mock()
            mock_get_prefs.return_value.get_vendor_preferences.return_value = mock_preferences
            mock_get_provider.return_value = mock_provider_manager
            
            # Item con precio óptimo
            optimal_item = BudgetItem(
                description="Hotel Estándar",
                amount=Decimal("100.00"),
                quantity=1,
                currency="USD",
                metadata={
                    "provider_id": "test_provider",
                    "category": "accommodation",
                    "rating": 4
                }
            )
            
            builder = BudgetBuilder(vendor_id="test_vendor")
            builder.add_item(optimal_item)
            
            # No deberían generarse sugerencias para items óptimos
            assert len(builder.get_suggestions()) == 0
