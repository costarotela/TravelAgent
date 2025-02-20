"""Tests para el optimizador de precios."""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal
import pytest

from smart_travel_agency.core.schemas import (
    TravelPackage,
    Flight,
    Accommodation,
    Activity,
    PricingStrategy
)
from smart_travel_agency.core.services import PackageService
from smart_travel_agency.core.analysis.price_optimizer.optimizer import (
    PriceOptimizer,
    PriceFactors,
)


class TestPriceOptimizer(unittest.IsolatedAsyncioTestCase):
    """Tests para el optimizador de precios."""

    def setUp(self):
        """Preparar datos de prueba."""
        self.optimizer = PriceOptimizer()
        self.package_service = PackageService()
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

    async def test_optimize_price(self):
        """Test de optimización de precio básica."""
        result = await self.optimizer.optimize_price(self.test_package)
        
        total_price = self.package_service.calculate_total_price(self.test_package)
        self.assertIsNotNone(result)
        self.assertGreater(result.optimal_price, total_price * Decimal("0.8"))
        self.assertLess(result.optimal_price, total_price * Decimal("1.2"))

    async def test_optimize_price_with_strategy(self):
        """Test de optimización con estrategia específica."""
        strategy = PricingStrategy(
            type="competitive",
            params={"margin": Decimal("0.15")}
        )
        result = await self.optimizer.optimize_price(self.test_package, strategy)
        
        total_price = self.package_service.calculate_total_price(self.test_package)
        self.assertIsNotNone(result)
        self.assertEqual(result.strategy.type, "competitive")

    async def test_optimize_prices_batch(self):
        """Test de optimización en lote."""
        packages = [self.test_package] * 3
        results = await self.optimizer.optimize_prices_batch(packages)
        self.assertEqual(len(results), 3)

    async def test_extract_price_factors(self):
        """Test de extracción de factores de precio."""
        factors = await self.optimizer._extract_price_factors(self.test_package)
        total_price = self.package_service.calculate_total_price(self.test_package)
        
        self.assertIsInstance(factors, PriceFactors)
        self.assertGreater(factors.base_cost, total_price * Decimal("0.5"))
        self.assertLess(factors.base_cost, total_price)

    async def test_invalid_package(self):
        """Test de manejo de paquete inválido."""
        with self.assertRaises(ValueError):
            await self.optimizer.optimize_price(None)

    async def test_seasonality_factor(self):
        """Test del factor de estacionalidad."""
        # Crear paquete para temporada alta (verano)
        summer_start = datetime(2024, 1, 15)
        summer_package = TravelPackage(
            destination="Rio de Janeiro",
            start_date=summer_start,
            end_date=summer_start + timedelta(days=7),
            price=Decimal("1000.00"),
            currency="USD",
            provider="Test Provider",
            description="Summer Package",
            flights=[self.test_flight],
            accommodation=self.test_accommodation,
            activities=[self.test_activity]
        )

        # Crear paquete para temporada baja (invierno)
        winter_start = datetime(2024, 7, 15)
        winter_package = TravelPackage(
            destination="Rio de Janeiro",
            start_date=winter_start,
            end_date=winter_start + timedelta(days=7),
            price=Decimal("1000.00"),
            currency="USD",
            provider="Test Provider",
            description="Winter Package",
            flights=[self.test_flight],
            accommodation=self.test_accommodation,
            activities=[self.test_activity]
        )

        summer_factors = await self.optimizer._extract_price_factors(summer_package)
        winter_factors = await self.optimizer._extract_price_factors(winter_package)

        self.assertGreater(summer_factors.seasonality, winter_factors.seasonality)

    async def test_select_strategy(self):
        """Verificar selección de estrategia."""
        strategy = await self.optimizer._select_strategy(self.test_package)

        # Verificar estrategia
        self.assertIsNotNone(strategy)
        self.assertIn(strategy.type, ["competitive", "value", "dynamic"])
        self.assertIsNotNone(strategy.params)

if __name__ == "__main__":
    unittest.main()
