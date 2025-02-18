"""Tests básicos para la aplicación principal."""

import unittest
from unittest.mock import patch, Mock, PropertyMock

from src.ui.main import initialize_session_state, handle_navigation, render_error
from src.utils.error_handling import AppError


class TestMainApp(unittest.TestCase):
    """Tests básicos para la aplicación principal."""

    def setUp(self):
        """Preparar tests."""
        self.session_state = {}
        self.patcher = patch("src.ui.main.st")
        self.mock_st = self.patcher.start()
        # Configurar session_state como propiedad
        type(self.mock_st).session_state = PropertyMock(return_value=self.session_state)

    def tearDown(self):
        """Limpiar tests."""
        self.patcher.stop()

    def test_initialize_session_state(self):
        """Verificar inicialización del estado de la sesión."""
        # Inicializar estado
        initialize_session_state()

        # Verificar estado inicial
        self.assertEqual(self.session_state["page"], "Inicio")
        self.assertIsNone(self.session_state["redirect_to"])

    def test_handle_navigation_with_redirect(self):
        """Verificar manejo de redirección."""
        # Configurar estado inicial
        self.session_state["page"] = "Inicio"
        self.session_state["redirect_to"] = "Búsqueda"

        # Configurar mock del sidebar
        self.mock_st.sidebar = Mock()
        self.mock_st.sidebar.button.return_value = False

        # Manejar navegación
        handle_navigation()

        # Verificar redirección
        self.assertEqual(self.session_state["page"], "Búsqueda")
        self.assertIsNone(self.session_state["redirect_to"])
        self.mock_st.rerun.assert_called_once()

    def test_render_error_page(self):
        """Verificar renderizado de página de error."""
        # Configurar estado inicial
        self.session_state["page"] = "Búsqueda"

        # Crear error de prueba
        test_error = AppError(
            error_type="TestError",
            message="Test error message",
            details={"test": "data"},
            traceback="test traceback",
        )

        # Simular que no se hace click en el botón
        self.mock_st.button.return_value = False
        render_error(test_error)

        # Verificar mensajes de error
        self.mock_st.error.assert_called_once_with(test_error.message)

        # Verificar que no hubo redirección
        self.assertEqual(self.session_state["page"], "Búsqueda")
        self.mock_st.rerun.assert_not_called()

        # Simular click en botón de inicio
        self.mock_st.reset_mock()
        self.mock_st.button.return_value = True
        render_error(test_error)

        # Verificar redirección
        self.assertEqual(self.session_state["page"], "Inicio")
        self.mock_st.rerun.assert_called_once()


if __name__ == "__main__":
    unittest.main()
