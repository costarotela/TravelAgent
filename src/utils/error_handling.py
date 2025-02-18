"""Módulo para manejo global de errores."""

from typing import Optional, Dict, Any, Type
from dataclasses import dataclass
from datetime import datetime
import traceback
import logging

from src.utils.monitoring import monitor


@dataclass
class AppError:
    """Clase para representar errores de la aplicación."""

    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    traceback: str = None

    def __post_init__(self):
        """Inicializar campos automáticos."""
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ValidationError(Exception):
    """Error de validación de datos."""

    pass


class NetworkError(Exception):
    """Error de conexión o red."""

    pass


class ResourceNotFoundError(Exception):
    """Error cuando no se encuentra un recurso."""

    pass


class AuthorizationError(Exception):
    """Error de autorización."""

    pass


ERROR_MESSAGES = {
    ValidationError: "Los datos proporcionados no son válidos",
    NetworkError: "Error de conexión. Por favor, verifique su conexión a internet",
    ResourceNotFoundError: "El recurso solicitado no fue encontrado",
    AuthorizationError: "No tiene permisos para realizar esta acción",
    Exception: "Ha ocurrido un error inesperado",
}


def get_error_message(error: Exception) -> str:
    """Obtener mensaje de error según el tipo de excepción."""
    for error_type, message in ERROR_MESSAGES.items():
        if isinstance(error, error_type):
            return message
    return ERROR_MESSAGES[Exception]


def handle_error(error: Exception, context: Dict[str, Any] = None) -> AppError:
    """
    Manejar un error y retornar un AppError con información estructurada.

    Args:
        error: La excepción a manejar
        context: Contexto adicional del error (opcional)

    Returns:
        AppError con la información del error
    """
    error_type = error.__class__.__name__
    message = get_error_message(error)

    # Obtener traceback
    tb = traceback.format_exc()

    # Crear AppError
    app_error = AppError(
        error_type=error_type, message=message, details=context, traceback=tb
    )

    # Registrar error
    logging.error(f"Error: {error_type}\nMessage: {message}\nContext: {context}\n{tb}")

    # Enviar métrica
    monitor.log_error(error, context or {})

    return app_error
