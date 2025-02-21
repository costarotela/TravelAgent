"""
Tests para la estrategia BEST_ALTERNATIVE del sistema de reconstrucción.

Fase 1:
- Búsqueda proactiva
- Sistema de scoring básico
- Logging y monitoreo
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from smart_travel_agency.core.budget.reconstructor import BudgetReconstructor
from smart_travel_agency.core.schemas import Budget, BudgetItem, ReconstructionStrategy

@pytest.fixture
def budget_item():
    """Fixture para crear un item de presupuesto base."""
    return BudgetItem(
        id="test_item_1",
        type="hotel",
        category="4_stars",
        price=Decimal("100.00"),
        cost=Decimal("80.00"),
        rating=4.0,
        availability=0.9,
        dates={
            "check_in": datetime.now(),
            "check_out": datetime.now() + timedelta(days=3)
        }
    )

@pytest.fixture
def budget(budget_item):
    """Fixture para crear un presupuesto de prueba."""
    return Budget(
        id="test_budget_1",
        items=[budget_item],
        criteria={
            "preferences": {
                "location": "beach",
                "amenities": ["pool", "wifi"]
            }
        },
        dates={
            "start": datetime.now(),
            "end": datetime.now() + timedelta(days=7)
        }
    )

@pytest.fixture
def reconstructor():
    """Fixture para crear instancia del reconstructor."""
    return BudgetReconstructor()

class TestBestAlternativePhase1:
    """Tests para la Fase 1 de la estrategia BEST_ALTERNATIVE."""

    async def test_detect_price_change(self, reconstructor, budget):
        """Verifica detección de cambios significativos de precio."""
        changes = {
            "cost_changes": {
                "test_item_1": Decimal("100.00")  # 25% incremento
            }
        }
        
        with patch.object(reconstructor, '_find_best_alternative') as mock_find:
            mock_find.return_value = None
            await reconstructor._best_alternative_strategy(budget, changes)
            
            # Verificar que se buscó alternativa
            mock_find.assert_called_once()

    async def test_score_calculation(self, reconstructor, budget_item):
        """Verifica cálculo correcto de scores."""
        # Item original
        original_score = reconstructor._calculate_item_score(budget_item)
        
        # Item más caro pero mejor rating
        expensive_item = budget_item.copy()
        expensive_item.price = Decimal("150.00")
        expensive_item.rating = 4.5
        expensive_score = reconstructor._calculate_item_score(expensive_item)
        
        # Item más barato pero peor rating
        cheap_item = budget_item.copy()
        cheap_item.price = Decimal("80.00")
        cheap_item.rating = 3.5
        cheap_score = reconstructor._calculate_item_score(cheap_item)
        
        # Verificar balance entre precio y rating
        assert original_score > expensive_score  # Precio tiene peso importante
        assert original_score > cheap_score  # Rating tiene peso importante

    async def test_find_best_alternative(self, reconstructor, budget, budget_item):
        """Verifica búsqueda y selección de mejor alternativa."""
        mock_provider = Mock()
        alternatives = [
            budget_item.copy(),  # Similar al original
            BudgetItem(  # Mejor alternativa
                id="alt_1",
                type="hotel",
                category="4_stars",
                price=Decimal("90.00"),
                cost=Decimal("70.00"),
                rating=4.2,
                availability=0.95
            ),
            BudgetItem(  # Peor alternativa
                id="alt_2",
                type="hotel",
                category="4_stars",
                price=Decimal("120.00"),
                cost=Decimal("100.00"),
                rating=3.8,
                availability=0.8
            )
        ]
        
        mock_provider.search_alternatives.return_value = alternatives
        
        with patch.object(reconstructor, '_get_active_providers') as mock_get_providers:
            mock_get_providers.return_value = [mock_provider]
            
            result = await reconstructor._find_best_alternative(
                item=budget_item,
                budget=budget,
                price_limit=Decimal("115.00")
            )
            
            # Verificar que se seleccionó la mejor alternativa
            assert result.id == "alt_1"
            assert result.price < budget_item.price
            assert result.rating > budget_item.rating

    async def test_logging_decisions(self, reconstructor, budget, caplog):
        """Verifica logging apropiado de decisiones."""
        changes = {
            "unavailable_items": ["test_item_1"]
        }
        
        with patch.object(reconstructor, '_find_best_alternative') as mock_find:
            mock_find.return_value = None
            await reconstructor._best_alternative_strategy(budget, changes)
            
            # Verificar mensajes de log
            assert "Buscando alternativa para item no disponible" in caplog.text

    @pytest.mark.parametrize("price_change,should_search", [
        (0.10, False),  # 10% cambio - No buscar
        (0.20, True),   # 20% cambio - Buscar
        (0.30, True),   # 30% cambio - Buscar
    ])
    async def test_price_change_threshold(
        self, reconstructor, budget, price_change, should_search
    ):
        """Verifica umbral de cambio de precio."""
        original_cost = budget.items[0].cost
        new_cost = original_cost * (1 + price_change)
        
        changes = {
            "cost_changes": {
                "test_item_1": new_cost
            }
        }
        
        with patch.object(reconstructor, '_find_best_alternative') as mock_find:
            mock_find.return_value = None
            await reconstructor._best_alternative_strategy(budget, changes)
            
            if should_search:
                mock_find.assert_called_once()
            else:
                mock_find.assert_not_called()
