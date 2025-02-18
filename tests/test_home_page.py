"""Tests básicos para la página de inicio."""

import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from src.core.budget.models import Budget, BudgetItem
from src.ui.pages.home import get_quick_stats, get_recent_activity


class TestHomePage(unittest.TestCase):
    """Tests básicos para las funciones de la página de inicio."""

    def setUp(self):
        """Preparar datos de prueba."""
        self.test_budgets = [
            Budget(
                id=f"TEST-00{i}",
                created_at=datetime.now(),
                valid_until=datetime.now(),
                customer_name=f"Cliente {i}",
                items=[
                    BudgetItem(
                        type="flight",
                        description="Test Flight",
                        unit_price=Decimal("100.00"),
                        quantity=2,
                        currency="USD",
                        details={
                            "flight_number": f"TF{i}",
                            "airline": "Test Air",
                            "cabin_class": "Economy",
                        },
                    )
                ],
                notes="Test notes",
                status="accepted" if i % 2 == 0 else "pending",
            )
            for i in range(1, 6)
        ]

    @patch("src.ui.pages.home.BudgetStorage")
    @patch("src.ui.pages.home.Database")
    def test_get_quick_stats(self, mock_db, mock_storage):
        """Verificar obtención de estadísticas rápidas."""
        # Configurar mock
        mock_storage_instance = Mock()
        mock_storage_instance.count_budgets.side_effect = [
            10,  # total
            4,  # accepted
            6,  # pending
        ]
        mock_storage.return_value = mock_storage_instance

        # Obtener estadísticas
        stats = get_quick_stats()

        # Verificar resultados
        self.assertIsNotNone(stats)
        self.assertEqual(stats["total"], 10)
        self.assertEqual(stats["accepted"], 4)
        self.assertEqual(stats["pending"], 6)
        self.assertEqual(stats["conversion"], 40.0)

        # Verificar llamadas
        mock_storage_instance.count_budgets.assert_any_call()
        mock_storage_instance.count_budgets.assert_any_call(status="accepted")
        mock_storage_instance.count_budgets.assert_any_call(status="pending")

    @patch("src.ui.pages.home.BudgetStorage")
    @patch("src.ui.pages.home.Database")
    def test_get_recent_activity(self, mock_db, mock_storage):
        """Verificar obtención de actividad reciente."""
        # Configurar mock
        mock_storage_instance = Mock()
        mock_storage_instance.get_recent_budgets.return_value = self.test_budgets
        mock_storage.return_value = mock_storage_instance

        # Obtener actividad reciente
        df = get_recent_activity()

        # Verificar resultados
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 5)
        self.assertTrue(
            all(
                col in df.columns
                for col in ["ID", "Cliente", "Fecha", "Estado", "Total"]
            )
        )

        # Verificar llamada
        mock_storage_instance.get_recent_budgets.assert_called_once_with(limit=5)


if __name__ == "__main__":
    unittest.main()
