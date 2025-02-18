"""Tests para el sistema de monitoreo OLA."""

import pytest
from unittest.mock import patch, MagicMock
from prometheus_client import Gauge, Counter
from src.core.monitoring.ola_monitor import OLAMonitor


@pytest.fixture
def mock_prometheus():
    """Fixture para mockear Prometheus."""
    with patch("prometheus_client.Gauge") as mock_gauge:
        with patch("prometheus_client.Counter") as mock_counter:
            with patch("prometheus_client.start_http_server") as mock_server:
                yield {
                    "gauge": mock_gauge,
                    "counter": mock_counter,
                    "server": mock_server,
                }


@pytest.fixture
def monitor(mock_prometheus):
    """Fixture para instancia de OLAMonitor."""
    return OLAMonitor(port=9090)


class TestOLAMonitor:
    """Suite de pruebas para OLAMonitor."""

    def test_monitor_initialization(self, mock_prometheus):
        """Probar inicialización del monitor."""
        monitor = OLAMonitor()

        # Verificar que se crearon todas las métricas
        assert mock_prometheus["gauge"].call_count >= 8  # Al menos 8 Gauges
        assert mock_prometheus["counter"].call_count >= 1  # Al menos 1 Counter

        # Verificar que se inició el servidor
        mock_prometheus["server"].assert_called_once_with(9090)

    def test_update_package_metrics(self, monitor):
        """Probar actualización de métricas de paquetes."""
        stats = {"total_nuevos": 5, "total_actualizados": 3, "total_eliminados": 1}
        destino = "Cancún"

        monitor.update_package_metrics(stats, destino)

        # Verificar que se actualizaron los valores
        monitor.paquetes_nuevos.labels.assert_called_with(destino=destino)
        monitor.paquetes_actualizados.labels.assert_called_with(destino=destino)
        monitor.paquetes_eliminados.labels.assert_called_with(destino=destino)

    def test_update_price_metrics(self, monitor):
        """Probar actualización de métricas de precios."""
        stats = {
            "precio_promedio": 1500.0,
            "precio_minimo": 1000.0,
            "precio_maximo": 2000.0,
        }
        destino = "Cancún"
        moneda = "USD"

        monitor.update_price_metrics(stats, destino, moneda)

        # Verificar llamadas a las métricas
        monitor.precio_promedio.labels.assert_called_with(
            destino=destino, moneda=moneda
        )
        monitor.precio_minimo.labels.assert_called_with(destino=destino, moneda=moneda)
        monitor.precio_maximo.labels.assert_called_with(destino=destino, moneda=moneda)

    def test_log_error(self, monitor):
        """Probar registro de errores."""
        tipo_error = "scraping_error"

        monitor.log_error(tipo_error)

        # Verificar incremento del contador
        monitor.error_counter.labels.assert_called_with(tipo_error=tipo_error)
        monitor.error_counter.labels(tipo_error=tipo_error).inc.assert_called_once()

    def test_update_performance_metrics(self, monitor):
        """Probar métricas de rendimiento."""
        tiempo = 1.5
        destino = "Cancún"

        monitor.update_performance_metrics(tiempo, destino)

        # Verificar actualización del tiempo
        monitor.tiempo_actualizacion.labels.assert_called_with(destino=destino)
        monitor.tiempo_actualizacion.labels(destino=destino).set.assert_called_with(
            tiempo
        )

    def test_update_scraping_duration(self, monitor):
        """Probar métricas de duración de scraping."""
        duracion = 2.5
        destino = "Cancún"

        monitor.update_scraping_duration(duracion, destino)

        # Verificar actualización de la duración
        monitor.scraping_duration.labels.assert_called_with(destino=destino)
        monitor.scraping_duration.labels(destino=destino).set.assert_called_with(
            duracion
        )

    def test_update_availability(self, monitor):
        """Probar métricas de disponibilidad."""
        porcentaje = 85.5
        destino = "Cancún"

        monitor.update_availability(porcentaje, destino)

        # Verificar actualización del porcentaje
        monitor.disponibilidad.labels.assert_called_with(destino=destino)
        monitor.disponibilidad.labels(destino=destino).set.assert_called_with(
            porcentaje
        )

    def test_server_start_error(self, mock_prometheus):
        """Probar manejo de error al iniciar servidor."""
        mock_prometheus["server"].side_effect = Exception("Error starting server")

        with pytest.raises(Exception) as exc_info:
            OLAMonitor()

        assert "Error starting server" in str(exc_info.value)
