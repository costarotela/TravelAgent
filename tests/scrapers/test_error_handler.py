"""Tests para el sistema de manejo de errores del scraper."""

import pytest
import asyncio
import logging
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from agent_core.scrapers.error_handler import (
    ErrorHandler,
    ScraperError,
    ConnectionError,
    AuthenticationError,
    DataExtractionError,
    BlockedError,
)


@pytest.fixture
def error_handler():
    """Fixture para crear un error handler de prueba."""
    return ErrorHandler("test_scraper")


@pytest.mark.asyncio
async def test_retry_success(error_handler):
    """Prueba reintentos exitosos."""
    mock_func = AsyncMock(side_effect=[ConnectionError("Error temporal"), "success"])

    @error_handler.with_retry("test_operation")
    async def test_operation():
        return await mock_func()

    # La operación debería tener éxito en el segundo intento
    result = await test_operation()
    assert result == "success"
    assert mock_func.call_count == 2


@pytest.mark.asyncio
async def test_retry_max_attempts(error_handler):
    """Prueba que se respeta el máximo de reintentos."""
    error = ConnectionError("Error persistente")
    mock_func = AsyncMock(side_effect=[error, error, error, error])

    @error_handler.with_retry("test_operation")
    async def test_operation():
        return await mock_func()

    # Debería fallar después de agotar los reintentos
    with pytest.raises(ConnectionError):
        await test_operation()

    # Verificar número de intentos (3 es el máximo para ConnectionError)
    assert mock_func.call_count == 3


@pytest.mark.asyncio
async def test_different_error_types(error_handler):
    """Prueba diferentes tipos de errores y sus configuraciones."""

    # AuthenticationError tiene max_retries=2
    error = AuthenticationError("Error de auth")
    mock_auth = AsyncMock(side_effect=[error, error, error])

    @error_handler.with_retry("auth_operation")
    async def auth_operation():
        return await mock_auth()

    with pytest.raises(AuthenticationError):
        await auth_operation()
    assert mock_auth.call_count == 2  # Solo 2 intentos

    # BlockedError tiene max_retries=1
    error = BlockedError("Sitio bloqueado")
    mock_blocked = AsyncMock(side_effect=[error, error])

    @error_handler.with_retry("blocked_operation")
    async def blocked_operation():
        return await mock_blocked()

    with pytest.raises(BlockedError):
        await blocked_operation()
    assert mock_blocked.call_count == 1  # Solo 1 intento


def test_error_handling(error_handler):
    """Prueba la conversión de errores genéricos a específicos."""

    # Error de conexión
    error = Exception("connection refused")
    result = error_handler.handle_error(error, "test_operation")
    assert isinstance(result, ConnectionError)

    # Error de autenticación
    error = Exception("invalid credentials")
    result = error_handler.handle_error(error, "login")
    assert isinstance(result, AuthenticationError)

    # Error de extracción
    error = Exception("element not found in page")
    result = error_handler.handle_error(error, "extract_data")
    assert isinstance(result, DataExtractionError)

    # Error de bloqueo
    error = Exception("captcha required")
    result = error_handler.handle_error(error, "search")
    assert isinstance(result, BlockedError)


@pytest.mark.asyncio
async def test_operation_metrics(error_handler):
    """Prueba el registro de métricas de operación."""

    with patch("prometheus_client.Counter.inc") as mock_counter, patch(
        "prometheus_client.Histogram.observe"
    ) as mock_histogram:

        # Operación exitosa
        mock_success = AsyncMock(return_value="success")

        @error_handler.with_retry("success_operation")
        async def success_operation():
            return await mock_success()

        result = await success_operation()
        assert result == "success"
        mock_histogram.assert_called_once()

        # Operación con reintento
        error = ConnectionError("Error temporal")
        mock_retry = AsyncMock(side_effect=[error, "success"])

        @error_handler.with_retry("retry_operation")
        async def retry_operation():
            return await mock_retry()

        result = await retry_operation()
        assert result == "success"
        assert mock_counter.call_count == 2  # Error + Retry


def test_logging(error_handler):
    """Prueba el logging de operaciones y errores."""
    logger = logging.getLogger("test_logger")
    logger.addHandler(logging.NullHandler())

    handler = ErrorHandler("test_scraper", logger)

    # Log de operación normal
    with patch.object(logger, "info") as mock_info:
        handler.log_operation("test_operation", param1="value1")
        mock_info.assert_called_once()

    # Log de error
    with patch.object(logger, "error") as mock_error:
        error = ScraperError("Test error")
        handler.log_operation("error_operation", error=str(error))
        mock_error.assert_not_called()  # Solo se registra en caso de error real


@pytest.mark.asyncio
async def test_backoff_timing(error_handler):
    """Prueba que el backoff exponencial funciona correctamente."""
    handler = ErrorHandler("test_scraper")
    error = ConnectionError("Error temporal")

    start_times = []
    mock_func = AsyncMock(side_effect=[error, error, error])

    @handler.with_retry("backoff_operation")
    async def backoff_operation():
        start_times.append(datetime.now())
        return await mock_func()

    with pytest.raises(ConnectionError):
        await backoff_operation()

    # Verificar que los intervalos entre intentos aumentan
    intervals = [
        (t2 - t1).total_seconds() for t1, t2 in zip(start_times[:-1], start_times[1:])
    ]

    # El primer reintento debería esperar ~2 segundos, el segundo ~4
    assert 1.5 <= intervals[0] <= 2.5
    assert 3.5 <= intervals[1] <= 4.5
