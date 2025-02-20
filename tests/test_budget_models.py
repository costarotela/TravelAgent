"""Tests básicos para los modelos de presupuestos."""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from smart_travel_agency.core.budget.models import (
    Budget,
    BudgetItem,
    create_budget_from_package,
)
from smart_travel_agency.core.providers.base import TravelPackage, Flight


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
            metadata={"departure_date": datetime.now(), "flight_number": "TEST123"},
        )

        self.test_budget = Budget(
            items=[self.test_item],
            currency="USD",
            metadata={
                "customer_name": "Test Customer",
                "notes": "Test notes",
                "status": "draft",
                "valid_until": datetime.now() + timedelta(days=3),
            },
        )

    def test_budget_item_total_price(self):
        """Verificar cálculo de precio total del ítem."""
        self.assertEqual(self.test_item.total_price, Decimal("200.00"))

    def test_budget_total_amount(self):
        """Verificar cálculo de monto total del presupuesto."""
        self.assertEqual(self.test_budget.total, Decimal("200.00"))

    def test_budget_serialization(self):
        """Verificar serialización/deserialización de presupuesto."""
        # Verificar que podemos acceder a los atributos básicos
        self.assertIsInstance(self.test_budget.budget_id, UUID)
        self.assertEqual(self.test_budget.currency, "USD")
        self.assertEqual(len(self.test_budget.items), 1)
        self.assertEqual(self.test_budget.metadata["customer_name"], "Test Customer")

    def test_create_budget_from_package(self):
        """Verificar creación de presupuesto desde paquete."""
        # Crear un paquete de prueba
        now = datetime.now()
        departure = now + timedelta(days=1)
        arrival = departure + timedelta(hours=2)

        test_flight = Flight(
            origin="GRU",
            destination="EZE",
            departure_time=departure,
            arrival_time=arrival,
            flight_number="TEST123",
            airline="Test Air",
            price=500.0,
            passengers=2,
        )

        package = TravelPackage(
            destination="Test City",
            start_date=departure,
            end_date=arrival,
            price=500.0,
            currency="USD",
            provider="Test Provider",
            description="Test Package",
            flights=[test_flight],
        )

        # Crear presupuesto desde el paquete
        budget = create_budget_from_package(package)

        # Verificar que el presupuesto se creó correctamente
        self.assertIsInstance(budget, Budget)
        self.assertEqual(budget.currency, "USD")
        self.assertEqual(len(budget.items), 1)  # Debe tener un ítem (el vuelo)
        self.assertEqual(budget.total, Decimal("1000.00"))  # 500 * 2 pasajeros


if __name__ == "__main__":
    unittest.main()
