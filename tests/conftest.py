"""
Configuración de pruebas y fixtures compartidos.
"""
import os
import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, AsyncMock

# Agregar el directorio raíz del proyecto al PYTHONPATH
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

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
    db.fetch_one = AsyncMock()
    db.fetch_all = AsyncMock()
    return db

# Mock de logger para pruebas
@pytest.fixture
def mock_logger():
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    return logger

# Mock de métricas para pruebas
@pytest.fixture
def mock_metrics():
    metrics = MagicMock()
    metrics.increment = MagicMock()
    return metrics

# Mock de eventos para pruebas
@pytest.fixture
def mock_events():
    events = MagicMock()
    events.publish = AsyncMock()
    events.subscribe = AsyncMock()
    events.unsubscribe = AsyncMock()
    return events
