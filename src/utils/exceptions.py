"""Excepciones personalizadas para el sistema."""


class ProviderError(Exception):
    """Error específico de proveedores de viaje."""

    pass


class ValidationError(Exception):
    """Error de validación de datos."""

    pass
