"""Tests básicos para el proveedor Aero."""

import unittest
import asyncio
from datetime import datetime, timedelta

from src.core.providers.aero import AeroProvider
from src.core.providers.base import SearchCriteria
from src.utils.exceptions import ValidationError


class TestAeroProvider(unittest.TestCase):
    """Tests básicos para AeroProvider."""

    def setUp(self):
        """Preparar datos de prueba."""
        self.provider = AeroProvider({"name": "test_aero"})
        self.valid_criteria = SearchCriteria(
            origin="GRU",
            destination="EZE",
            departure_date=datetime.now() + timedelta(days=1),
            return_date=None,
            adults=2,
            children=1,
            cabin_class="ECONOMY",
        )

    def test_validate_criteria(self):
        """Verificar validación de criterios de búsqueda."""
        # Criterios válidos
        self.provider._validate_criteria(self.valid_criteria)

        # Criterios inválidos - fecha pasada
        invalid_criteria = SearchCriteria(
            origin="GRU",
            destination="EZE",
            departure_date=datetime.now() - timedelta(days=1),
            adults=1,
        )
        with self.assertRaises(ValidationError):
            self.provider._validate_criteria(invalid_criteria)

        # Criterios inválidos - código IATA
        invalid_criteria = SearchCriteria(
            origin="GRUU",
            destination="EZE",
            departure_date=datetime.now() + timedelta(days=1),
            adults=1,
        )
        with self.assertRaises(ValidationError):
            self.provider._validate_criteria(invalid_criteria)

    def test_cache_key_generation(self):
        """Verificar generación de claves de caché."""
        key = self.provider._get_cache_key(self.valid_criteria)
        expected_key = f"GRU:EZE:{self.valid_criteria.departure_date.date()}:ECONOMY"
        self.assertEqual(key, expected_key)

    def test_search_results(self):
        """Verificar resultados de búsqueda."""

        async def run_search():
            results = await self.provider._search(self.valid_criteria)
            self.assertIsNotNone(results)
            self.assertTrue(len(results) > 0)

            # Verificar datos de resultado
            first_result = results[0]
            self.assertEqual(first_result.origin, "GRU")
            self.assertEqual(first_result.destination, "EZE")
            self.assertIsNotNone(first_result.price)
            self.assertEqual(first_result.currency, "USD")

            # Verificar detalles
            self.assertIn("flight_number", first_result.details)
            self.assertIn("airline", first_result.details)
            self.assertIn("baggage", first_result.details)

        asyncio.run(run_search())

    def test_cache_functionality(self):
        """Verificar funcionamiento del caché."""

        async def run_cache_test():
            # Primera búsqueda
            results1 = await self.provider._search(self.valid_criteria)

            # Segunda búsqueda (debería venir del caché)
            results2 = await self.provider._search(self.valid_criteria)

            # Verificar que los resultados son iguales
            self.assertEqual(len(results1), len(results2))
            self.assertEqual(results1[0].id, results2[0].id)

        asyncio.run(run_cache_test())


if __name__ == "__main__":
    unittest.main()
