"""
Configuración de pruebas y fixtures compartidos.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock


# Mock de caché para pruebas
@pytest.fixture
def mock_cache():
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache


# Mock de base de datos para pruebas
@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.fetch = AsyncMock(return_value=[])
    return db


# Mock de logger para pruebas
@pytest.fixture
def mock_logger():
    return MagicMock()


# Mock de métricas para pruebas
@pytest.fixture
def mock_metrics():
    return MagicMock()


# Mock de eventos para pruebas
@pytest.fixture
def mock_events():
    events = MagicMock()
    events.emit = AsyncMock()
    events.subscribe = MagicMock()
    return events
