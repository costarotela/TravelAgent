"""Tests para el manejo de errores."""

import unittest
from unittest.mock import patch, Mock
from datetime import datetime

from src.utils.error_handling import (
    AppError,
    ValidationError,
    NetworkError,
    ResourceNotFoundError,
    AuthorizationError,
    get_error_message,
    handle_error,
)


class TestErrorHandling(unittest.TestCase):
    """Tests para el manejo de errores."""

    def test_app_error_initialization(self):
        """Verificar inicialización de AppError."""
        # Crear error básico
        error = AppError(error_type="TestError", message="Test message")

        # Verificar campos automáticos
        self.assertIsNotNone(error.timestamp)
        self.assertIsInstance(error.timestamp, datetime)
        self.assertIsNone(error.details)
        self.assertIsNone(error.traceback)

        # Crear error con todos los campos
        details = {"test": "data"}
        traceback = "test traceback"
        timestamp = datetime.now()

        error = AppError(
            error_type="TestError",
            message="Test message",
            details=details,
            traceback=traceback,
            timestamp=timestamp,
        )

        # Verificar todos los campos
        self.assertEqual(error.error_type, "TestError")
        self.assertEqual(error.message, "Test message")
        self.assertEqual(error.details, details)
        self.assertEqual(error.traceback, traceback)
        self.assertEqual(error.timestamp, timestamp)

    def test_get_error_message(self):
        """Verificar obtención de mensajes de error."""
        # Verificar mensajes específicos
        self.assertEqual(
            get_error_message(ValidationError()),
            "Los datos proporcionados no son válidos",
        )
        self.assertEqual(
            get_error_message(NetworkError()),
            "Error de conexión. Por favor, verifique su conexión a internet",
        )
        self.assertEqual(
            get_error_message(ResourceNotFoundError()),
            "El recurso solicitado no fue encontrado",
        )
        self.assertEqual(
            get_error_message(AuthorizationError()),
            "No tiene permisos para realizar esta acción",
        )

        # Verificar mensaje por defecto
        class UnknownError(Exception):
            pass

        self.assertEqual(
            get_error_message(UnknownError()), "Ha ocurrido un error inesperado"
        )

    @patch("src.utils.error_handling.logging")
    @patch("src.utils.error_handling.monitor")
    def test_handle_error(self, mock_monitor, mock_logging):
        """Verificar manejo de errores."""
        # Crear error de prueba
        test_error = ValidationError("datos inválidos")
        test_context = {"user_id": "123"}

        # Manejar error
        app_error = handle_error(test_error, test_context)

        # Verificar AppError
        self.assertEqual(app_error.error_type, "ValidationError")
        self.assertEqual(app_error.message, "Los datos proporcionados no son válidos")
        self.assertEqual(app_error.details, test_context)
        self.assertIsNotNone(app_error.traceback)
        self.assertIsInstance(app_error.timestamp, datetime)

        # Verificar logging
        mock_logging.error.assert_called_once()

        # Verificar monitor
        mock_monitor.log_error.assert_called_once_with(test_error, test_context)


if __name__ == "__main__":
    unittest.main()
