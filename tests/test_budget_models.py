"""Tests básicos para los modelos de presupuestos."""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from src.core.budget.models import Budget, BudgetItem, create_budget_from_package
from src.core.providers.base import TravelPackage


class TestBudgetModels(unittest.TestCase):
    """Tests básicos para Budget y BudgetItem."""

    def setUp(self):
        """Preparar datos de prueba."""
        self.test_item = BudgetItem(
            type="flight",
            description="Test Flight",
            unit_price=Decimal("100.00"),
            quantity=2,
            currency="USD",
            details={"departure_date": datetime.now(), "flight_number": "TEST123"},
        )

        self.test_budget = Budget(
            id="TEST-001",
            created_at=datetime.now(),
            valid_until=datetime.now() + timedelta(days=3),
            customer_name="Test Customer",
            items=[self.test_item],
            notes="Test notes",
            status="draft",
        )

    def test_budget_item_total_price(self):
        """Verificar cálculo de precio total del ítem."""
        self.assertEqual(self.test_item.total_price, Decimal("200.00"))

    def test_budget_total_amount(self):
        """Verificar cálculo de monto total del presupuesto."""
        totals = self.test_budget.total_amount
        self.assertEqual(totals["USD"], Decimal("200.00"))

    def test_budget_serialization(self):
        """Verificar serialización/deserialización de presupuesto."""
        budget_dict = self.test_budget.to_dict()
        restored_budget = Budget.from_dict(budget_dict)

        self.assertEqual(restored_budget.id, self.test_budget.id)
        self.assertEqual(restored_budget.customer_name, self.test_budget.customer_name)
        self.assertEqual(len(restored_budget.items), len(self.test_budget.items))

    def test_create_budget_from_package(self):
        """Verificar creación de presupuesto desde paquete."""
        # Crear paquete de prueba
        test_package = TravelPackage(
            id="PKG-001",
            provider="test_provider",
            origin="GRU",
            destination="EZE",
            departure_date=datetime.now() + timedelta(days=1),
            return_date=None,
            price=100.0,
            currency="USD",
            availability=True,
            details={
                "flight_number": "TEST123",
                "airline": "Test Air",
                "cabin_class": "ECONOMY",
                "baggage": "23kg",
            },
        )

        # Crear presupuesto desde paquete
        budget = create_budget_from_package(
            package=test_package,
            customer_name="Test Customer",
            passengers={"adults": 2, "children": 1},
            valid_days=3,
        )

        # Verificar datos básicos
        self.assertIsNotNone(budget.id)
        self.assertEqual(budget.customer_name, "Test Customer")
        self.assertEqual(len(budget.items), 1)
        self.assertEqual(budget.items[0].quantity, 3)  # 2 adultos + 1 niño
        self.assertEqual(budget.status, "draft")


if __name__ == "__main__":
    unittest.main()
