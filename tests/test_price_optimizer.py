"""Tests para el optimizador de precios."""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal
import pytest

from smart_travel_agency.core.analysis.price_optimizer.optimizer import (
    PriceOptimizer,
    PriceFactors,
)
from smart_travel_agency.core.schemas import (
    TravelPackage,
    PricingStrategy,
    Flight,
    Accommodation,
    Activity,
)


class TestPriceOptimizer(unittest.IsolatedAsyncioTestCase):
    """Tests para el optimizador de precios."""

    def setUp(self):
        """Preparar datos de prueba."""
        self.optimizer = PriceOptimizer()
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
            price=500.0,
            passengers=2
        )

        # Crear alojamiento de prueba
        self.test_accommodation = Accommodation(
            hotel_id="TEST_HOTEL",
            name="Test Hotel",
            room_type="Standard",
            price_per_night=200.0,
            nights=7,
            check_in=self.start_date,
            check_out=self.end_date
        )

        # Crear actividad de prueba
        self.test_activity = Activity(
            activity_id="TEST_ACT",
            name="City Tour",
            price=100.0,
            duration=timedelta(hours=4),
            participants=2,
            date=self.start_date + timedelta(days=1)
        )

        # Crear paquete de prueba
        self.test_package = TravelPackage(
            destination="Test City",
            start_date=self.start_date,
            end_date=self.end_date,
            price=2000.0,
            currency="USD",
            provider="Test Provider",
            description="Test Package",
            flights=[self.test_flight],
            accommodation=self.test_accommodation,
            activities=[self.test_activity]
        )

    async def test_optimize_price(self):
        """Verificar optimización de precio básica."""
        # Optimizar precio sin estrategia específica
        result = await self.optimizer.optimize_price(self.test_package)

        # Verificar resultado
        self.assertIsNotNone(result)
        self.assertGreater(result.optimal_price, 0)
        self.assertGreater(result.margin, 0)
        self.assertGreater(result.roi, 0)
        self.assertIsNotNone(result.metadata)

    async def test_optimize_price_with_strategy(self):
        """Verificar optimización con estrategia específica."""
        # Crear estrategia competitiva
        strategy = PricingStrategy(
            type="competitive",
            params={"margin": 0.2, "weight": 0.4}
        )

        # Optimizar precio con estrategia
        result = await self.optimizer.optimize_price(self.test_package, strategy)

        # Verificar resultado
        self.assertIsNotNone(result)
        self.assertEqual(result.strategy.type, "competitive")
        self.assertGreater(result.optimal_price, 0)

    async def test_optimize_prices_batch(self):
        """Verificar optimización de múltiples paquetes."""
        # Crear lista de paquetes
        packages = []
        for _ in range(3):
            package = TravelPackage(
                package_id = f"package_{_}",
                destination=self.test_package.destination,
                start_date=self.test_package.start_date,
                end_date=self.test_package.end_date,
                price=self.test_package.price,
                currency=self.test_package.currency,
                provider=self.test_package.provider,
                description=self.test_package.description,
                flights=self.test_package.flights,
                accommodation=self.test_package.accommodation,
                activities=self.test_package.activities,
            )
            packages.append(package)

        # Optimizar precios
        results = await self.optimizer.optimize_prices(packages)

        # Verificar resultados
        self.assertEqual(len(results), 3)
        for result in results.values():
            self.assertIsNotNone(result)
            self.assertGreater(result.optimal_price, 0)

    async def test_extract_price_factors(self):
        """Verificar extracción de factores de precio."""
        # Extraer factores
        factors = await self.optimizer._extract_price_factors(self.test_package)

        # Verificar factores
        self.assertIsInstance(factors, PriceFactors)
        self.assertGreater(factors.base_cost, 0)
        self.assertGreaterEqual(factors.margin, 0)
        self.assertGreater(factors.seasonality, 0)
        self.assertGreaterEqual(factors.demand, 0)
        self.assertGreaterEqual(factors.competition, 0)
        self.assertGreaterEqual(factors.quality, 0)
        self.assertGreaterEqual(factors.flexibility, 0)

    async def test_select_strategy(self):
        """Verificar selección de estrategia."""
        # Seleccionar estrategia
        strategy = await self.optimizer._select_strategy(self.test_package)

        # Verificar estrategia
        self.assertIsNotNone(strategy)
        self.assertIn(strategy.type, ["competitive", "value", "dynamic"])
        self.assertIsNotNone(strategy.params)

    async def test_invalid_package(self):
        """Verificar manejo de paquete inválido."""
        with self.assertRaises(ValueError) as cm:
            await self.optimizer.optimize_price(None)
        self.assertEqual(str(cm.exception), "El paquete no puede ser None")

    async def test_seasonality_factor(self):
        """Verificar cálculo de factor estacional."""
        # Calcular factor para diferentes fechas
        summer = await self.optimizer.get_seasonality_factor(
            datetime(2024, 1, 15),  # Verano
            "Test City"
        )
        winter = await self.optimizer.get_seasonality_factor(
            datetime(2024, 7, 15),  # Invierno
            "Test City"
        )

        # Verificar factores
        self.assertGreater(summer, winter)  # El verano debe tener mayor factor


if __name__ == "__main__":
    unittest.main()
