"""Tests básicos para la página de búsqueda."""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from src.core.providers import TravelPackage
from src.ui.pages.search import filter_results, create_budget_from_flight


class TestSearchPage(unittest.TestCase):
    """Tests básicos para las funciones de la página de búsqueda."""

    def setUp(self):
        """Preparar datos de prueba."""
        self.test_flights = [
            TravelPackage(
                id="TEST-001",
                provider="test",
                origin="GRU",
                destination="EZE",
                departure_date=datetime.now() + timedelta(days=1),
                return_date=None,
                price=500.0,
                currency="USD",
                availability=True,
                details={
                    "airline": "Test Air",
                    "flight_number": "TA123",
                    "cabin_class": "Economy",
                    "baggage": "23kg",
                },
            ),
            TravelPackage(
                id="TEST-002",
                provider="test",
                origin="GRU",
                destination="EZE",
                departure_date=datetime.now() + timedelta(days=1),
                return_date=None,
                price=1000.0,
                currency="USD",
                availability=True,
                details={
                    "airline": "Test Air",
                    "flight_number": "TA456",
                    "cabin_class": "Business",
                    "baggage": "32kg",
                },
            ),
        ]

    def test_filter_results(self):
        """Verificar filtrado de resultados por precio."""
        # Sin filtro de precio
        results = filter_results(self.test_flights)
        self.assertEqual(len(results), 2)

        # Con filtro de precio que incluye todos
        results = filter_results(self.test_flights, 1500.0)
        self.assertEqual(len(results), 2)

        # Con filtro de precio que incluye solo el económico
        results = filter_results(self.test_flights, 750.0)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, "TEST-001")

        # Con filtro de precio que no incluye ninguno
        results = filter_results(self.test_flights, 100.0)
        self.assertEqual(len(results), 0)

    @patch("src.ui.pages.search.BudgetStorage")
    @patch("src.ui.pages.search.Database")
    @patch("src.ui.pages.search.st")
    @patch("src.ui.pages.search.monitor")
    @patch("src.ui.pages.search.create_budget_from_package")
    def test_create_budget_from_flight(
        self, mock_create_budget, mock_monitor, mock_st, mock_db, mock_storage
    ):
        """Verificar creación de presupuesto desde vuelo."""
        # Configurar mocks
        mock_budget = Mock()
        mock_create_budget.return_value = mock_budget

        mock_storage_instance = Mock()
        mock_storage_instance.save_budget.return_value = "TEST-BUDGET-001"
        mock_storage.return_value = mock_storage_instance

        mock_st.session_state = Mock()

        # Probar creación exitosa
        result = create_budget_from_flight(self.test_flights[0], 2)
        self.assertTrue(result)

        # Verificar llamada a create_budget_from_package
        mock_create_budget.assert_called_once_with(
            package=self.test_flights[0],
            customer_name="Cliente Nuevo",
            passengers={"adults": 2},
            valid_days=3,
        )

        # Verificar que se llamó a save_budget
        mock_storage_instance.save_budget.assert_called_once_with(mock_budget)

        # Verificar que se actualizó el estado de la sesión
        self.assertEqual(mock_st.session_state.selected_budget_id, "TEST-BUDGET-001")
        self.assertEqual(mock_st.session_state.redirect_to, "Presupuestos")

        # Verificar métricas
        mock_monitor.log_metric.assert_called_once_with(
            "budget_created", 1, {"type": "flight"}
        )

        # Probar error en creación
        mock_storage_instance.save_budget.side_effect = Exception("Test error")
        result = create_budget_from_flight(self.test_flights[0], 2)
        self.assertFalse(result)
        mock_st.error.assert_called_once()
        mock_monitor.log_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
