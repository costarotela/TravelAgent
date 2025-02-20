"""Tests básicos para los modelos de presupuestos."""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from smart_travel_agency.core.schemas import (
    TravelPackage,
    Flight,
    Accommodation,
    Activity
)
from smart_travel_agency.core.services import PackageService
from smart_travel_agency.core.budget.models import (
    Budget,
    BudgetItem,
    create_budget_from_package,
)


class TestBudgetModels(unittest.TestCase):
    """Tests básicos para Budget y BudgetItem."""

    def setUp(self):
        """Preparar datos de prueba."""
        self.now = datetime.now()
        self.start_date = self.now + timedelta(days=30)
        self.end_date = self.start_date + timedelta(days=7)

        # Crear vuelo de prueba
        self.test_flight = Flight(
            origin="GRU",
            destination="EZE",
            departure_time=self.start_date,
            arrival_time=self.start_date + timedelta(hours=2),
            flight_number="TEST123",
            airline="Test Air",
            price=Decimal("500.00"),
            passengers=2
        )

        # Crear alojamiento de prueba
        self.test_accommodation = Accommodation(
            hotel_id="TEST_HOTEL",
            name="Test Hotel",
            room_type="Standard",
            price_per_night=Decimal("200.00"),
            nights=7,
            check_in=self.start_date,
            check_out=self.end_date
        )

        # Crear actividad de prueba
        self.test_activity = Activity(
            activity_id="TEST_ACT",
            name="City Tour",
            price=Decimal("100.00"),
            duration=timedelta(hours=4),
            participants=2,
            date=self.start_date + timedelta(days=1)
        )

        # Crear paquete de prueba
        self.test_package = TravelPackage(
            destination="Buenos Aires",
            start_date=self.start_date,
            end_date=self.end_date,
            price=Decimal("1000.00"),  # Precio base
            currency="USD",
            provider="Test Provider",
            description="Test Package",
            flights=[self.test_flight],
            accommodation=self.test_accommodation,
            activities=[self.test_activity]
        )

        # Crear item de presupuesto
        self.test_item = BudgetItem(
            description="Test Item",
            amount=Decimal("100.00"),
            quantity=2,
            currency="USD"
        )

    def test_budget_item_total_price(self):
        """Verificar cálculo de precio total del item."""
        self.assertEqual(
            self.test_item.total_amount,
            Decimal("200.00")
        )

    def test_budget_total_amount(self):
        """Verificar cálculo de monto total del presupuesto."""
        budget = Budget(
            items=[
                BudgetItem(
                    description="Item 1",
                    amount=Decimal("100.00"),
                    quantity=2,
                    currency="USD"
                ),
                BudgetItem(
                    description="Item 2",
                    amount=Decimal("50.00"),
                    quantity=1,
                    currency="USD"
                )
            ],
            currency="USD"
        )
        self.assertEqual(budget.total_amount, Decimal("250.00"))

    def test_budget_serialization(self):
        """Verificar serialización del presupuesto."""
        budget = Budget(
            items=[self.test_item],
            currency="USD"
        )
        data = budget.to_dict()
        
        self.assertEqual(data["currency"], "USD")
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(
            Decimal(data["items"][0]["amount"]),
            self.test_item.amount
        )

    def test_create_budget_from_package(self):
        """Verificar creación de presupuesto desde paquete."""
        budget = create_budget_from_package(self.test_package)
        
        self.assertIsInstance(budget, Budget)
        self.assertEqual(budget.currency, self.test_package.currency)
        self.assertEqual(budget.total_amount, self.test_package.total_price)


if __name__ == "__main__":
    unittest.main()
