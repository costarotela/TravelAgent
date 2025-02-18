"""Tests para el actualizador dinámico OLA."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from bs4 import BeautifulSoup
from src.core.providers.ola_dynamic_updater import OLAUpdater
from src.core.monitoring.ola_monitor import OLAMonitor
from src.core.providers.ola_models import PaqueteOLA

@pytest.fixture
def mock_monitor():
    """Fixture para mockear OLAMonitor."""
    monitor = MagicMock(spec=OLAMonitor)
    return monitor

@pytest.fixture
def mock_browser():
    """Fixture para mockear SmartBrowser."""
    with patch('src.core.browsers.smart_browser.SmartBrowser') as mock:
        browser = AsyncMock()
        mock.return_value = browser
        yield browser

@pytest.fixture
def sample_config():
    """Fixture para configuración de prueba."""
    return {
        'base_url': 'https://test-ola.com',
        'headless': True,
        'cache_size': 100,
        'cache_ttl': 3600
    }

@pytest.fixture
def updater(sample_config, mock_monitor):
    """Fixture para instancia de OLAUpdater."""
    return OLAUpdater(sample_config, monitor=mock_monitor)

@pytest.fixture
def sample_html():
    """Fixture para HTML de prueba."""
    return """
    <div class="paquete-item">
        <div class="destino">Cancún</div>
        <div class="precio">$1500.00</div>
        <div class="aerolinea">AeroMéxico</div>
        <div class="duracion">7 días</div>
        <ul class="servicios-incluidos">
            <li>Vuelo</li>
            <li>Hotel</li>
        </ul>
        <div class="vuelos-info">
            <div class="vuelo">
                <div class="hora-salida">08:00</div>
                <div class="hora-llegada">10:00</div>
                <div class="duracion">2h</div>
                <div class="aerolinea">AeroMéxico</div>
            </div>
        </div>
        <div class="politicas-cancelacion">
            <div class="periodo-1">Reembolso completo</div>
            <div class="periodo-2">50% reembolso</div>
            <div class="periodo-3">No reembolsable</div>
        </div>
    </div>
    """

@pytest.mark.asyncio
class TestOLAUpdater:
    """Suite de pruebas para OLAUpdater."""

    async def test_fetch_data(self, updater, mock_browser, sample_html):
        """Probar obtención de datos."""
        mock_browser.get_soup.return_value = BeautifulSoup(sample_html, 'html.parser')
        mock_browser.__aenter__.return_value = mock_browser
        
        result = await updater.fetch_data("Cancún")
        
        assert 'stats' in result
        assert 'details' in result
        assert result['stats']['total_nuevos'] >= 0
        
        # Verificar llamadas al monitor
        updater.monitor.update_scraping_duration.assert_called_once()
        updater.monitor.update_package_metrics.assert_called_once()

    def test_normalize_data(self, updater, sample_html):
        """Probar normalización de datos."""
        soup = BeautifulSoup(sample_html, 'html.parser')
        raw_data = [{
            'destino': 'Cancún',
            'precio': 1500.0,
            'aerolinea': 'AeroMéxico',
            'duracion': 7,
            'incluye': ['Vuelo', 'Hotel'],
            'vuelos': [{
                'salida': '08:00',
                'llegada': '10:00',
                'duracion': '2h',
                'aerolinea': 'AeroMéxico'
            }],
            'politicas_cancelacion': {
                "0-61 noches antes": "Reembolso completo",
                "62-90 noches antes": "50% reembolso",
                "91+ noches antes": "No reembolsable"
            }
        }]
        
        normalized = updater._normalize_data(raw_data)
        
        assert len(normalized) == 1
        assert isinstance(normalized[0], PaqueteOLA)
        assert normalized[0].destino == 'Cancún'
        assert normalized[0].precio == 1500.0

    def test_detect_changes(self, updater):
        """Probar detección de cambios."""
        # Crear paquetes de prueba
        paquete1 = PaqueteOLA(
            destino="Cancún",
            origen="Buenos Aires",
            duracion=7,
            aerolinea="AeroMéxico",
            moneda="USD",
            precio=1500.0,
            impuestos=200.0,
            fechas=[datetime.now()],
            incluye=["Vuelo", "Hotel"],
            vuelos=[{
                "salida": "08:00",
                "llegada": "10:00",
                "duracion": "2h",
                "aerolinea": "AeroMéxico"
            }],
            politicas_cancelacion={
                "0-61 noches antes": "Reembolso completo",
                "62-90 noches antes": "50% reembolso",
                "91+ noches antes": "No reembolsable"
            }
        )
        
        # Detectar nuevo paquete
        changes = updater._detect_changes([paquete1])
        assert len(changes['nuevos']) == 1
        assert len(changes['actualizados']) == 0
        assert len(changes['eliminados']) == 0
        
        # Detectar actualización
        paquete1.precio = 1600.0
        changes = updater._detect_changes([paquete1])
        assert len(changes['nuevos']) == 0
        assert len(changes['actualizados']) == 1
        assert len(changes['eliminados']) == 0

    def test_process_updates(self, updater):
        """Probar procesamiento de actualizaciones."""
        changes = {
            'nuevos': [MagicMock(spec=PaqueteOLA)],
            'actualizados': [MagicMock(spec=PaqueteOLA)],
            'eliminados': ['hash1', 'hash2']
        }
        
        report = updater._process_updates(changes, "Cancún")
        
        assert report['stats']['total_nuevos'] == 1
        assert report['stats']['total_actualizados'] == 1
        assert report['stats']['total_eliminados'] == 2

    def test_generate_hash(self, updater):
        """Probar generación de hash."""
        data = {
            'destino': 'Cancún',
            'precio': 1500.0,
            'aerolinea': 'AeroMéxico'
        }
        
        hash1 = updater._generate_hash(data)
        
        # Modificar precio
        data['precio'] = 1600.0
        hash2 = updater._generate_hash(data)
        
        assert isinstance(hash1, str)
        assert hash1 != hash2  # Hashes diferentes para datos diferentes

    async def test_error_handling(self, updater, mock_browser):
        """Probar manejo de errores."""
        mock_browser.__aenter__.return_value = mock_browser
        mock_browser.navigate.side_effect = Exception("Connection error")
        
        with pytest.raises(Exception) as exc_info:
            await updater.fetch_data("Cancún")
        
        assert "Connection error" in str(exc_info.value)
        updater.monitor.log_error.assert_called_once()
