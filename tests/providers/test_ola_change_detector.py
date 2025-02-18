"""Tests para el detector de cambios OLA."""

import pytest
from datetime import datetime
from src.core.providers.ola_models import PaqueteOLA, Vuelo, PoliticasCancelacion
from src.core.providers.ola_change_detector import OLAChangeDetector


@pytest.fixture
def detector():
    """Fixture para el detector de cambios."""
    return OLAChangeDetector()


@pytest.fixture
def sample_package():
    """Fixture para un paquete de ejemplo."""
    return PaqueteOLA(
        destino="Cancún",
        aerolinea="AeroMéxico",
        origen="Buenos Aires",
        duracion=7,
        moneda="USD",
        incluye=["Vuelo", "Hotel"],
        fechas=[datetime(2025, 12, 25), datetime(2025, 12, 26)],
        precio=1500.0,
        impuestos=200.0,
        politicas_cancelacion=PoliticasCancelacion(
            **{
                "0-61 noches antes": "Reembolso completo",
                "62-90 noches antes": "50% reembolso",
                "91+ noches antes": "No reembolsable",
            }
        ),
        vuelos=[
            Vuelo(
                salida="08:00", llegada="10:00", duracion="2h", aerolinea="AeroMéxico"
            )
        ],
        data_hash="abc123",
    )


class TestOLAChangeDetector:
    """Suite de pruebas para OLAChangeDetector."""

    def test_detect_new_package(self, detector, sample_package):
        """Probar detección de paquete nuevo."""
        changes = detector.detect_changes([sample_package])

        assert len(changes["nuevos"]) == 1
        assert len(changes["actualizados"]) == 0
        assert len(changes["eliminados"]) == 0
        assert changes["nuevos"][0].data_hash == sample_package.data_hash

    def test_detect_updated_package(self, detector, sample_package):
        """Probar detección de paquete actualizado."""
        # Primera detección
        detector.detect_changes([sample_package])

        # Modificar precio
        updated_package = sample_package.model_copy(deep=True)
        updated_package.precio = 1600.0

        # Segunda detección
        changes = detector.detect_changes([updated_package])

        assert len(changes["nuevos"]) == 0
        assert len(changes["actualizados"]) == 1
        assert len(changes["eliminados"]) == 0
        assert changes["actualizados"][0].precio == 1600.0

    def test_detect_deleted_package(self, detector, sample_package):
        """Probar detección de paquete eliminado."""
        # Primera detección
        detector.detect_changes([sample_package])

        # Segunda detección sin paquetes
        changes = detector.detect_changes([])

        assert len(changes["nuevos"]) == 0
        assert len(changes["actualizados"]) == 0
        assert len(changes["eliminados"]) == 1
        assert sample_package.data_hash in changes["eliminados"]

    def test_analyze_price_changes(self, detector, sample_package):
        """Probar análisis de cambios en precios."""
        # Primera detección
        detector.detect_changes([sample_package])

        # Modificar precio
        updated_package = sample_package.model_copy(deep=True)
        updated_package.precio = 1600.0

        # Segunda detección
        changes = detector.detect_changes([updated_package])

        # Analizar cambios
        stats = detector.analyze_changes(changes)
        price_details = stats["detalles"]["precio"]

        assert price_details["total_cambios"] == 1
        assert len(price_details["cambios"]) == 1
        assert price_details["cambios"][0]["diferencia"] == 100.0
        assert abs(price_details["cambios"][0]["porcentaje"] - 6.67) < 0.01

    def test_analyze_availability(self, detector, sample_package):
        """Probar análisis de disponibilidad."""
        # Primera detección con dos paquetes
        package2 = sample_package.model_copy(deep=True)
        package2.data_hash = "def456"
        detector.detect_changes([sample_package, package2])

        # Segunda detección con un paquete eliminado
        changes = detector.detect_changes([sample_package])
        stats = detector.analyze_changes(changes)

        availability = stats["detalles"]["disponibilidad"]
        assert availability["total_paquetes"] == 2
        assert availability["paquetes_disponibles"] == 1
        assert availability["porcentaje_disponible"] == 50.0

    def test_analyze_date_changes(self, detector, sample_package):
        """Probar análisis de cambios en fechas."""
        # Primera detección
        detector.detect_changes([sample_package])

        # Modificar fechas
        updated_package = sample_package.model_copy(deep=True)
        updated_package.fechas = [
            datetime(2025, 12, 25),
            datetime(2025, 12, 26),
            datetime(2025, 12, 27),  # Nueva fecha
        ]

        # Segunda detección
        changes = detector.detect_changes([updated_package])
        stats = detector.analyze_changes(changes)

        date_details = stats["detalles"]["fechas"]
        assert date_details["total_cambios"] == 1
        assert len(date_details["cambios"]) == 1
        assert len(date_details["cambios"][0]["fechas_nuevas"]) == 1
        assert len(date_details["cambios"][0]["fechas_eliminadas"]) == 0

    def test_no_changes_detected(self, detector, sample_package):
        """Probar que no se detectan cambios cuando no hay."""
        # Primera detección
        detector.detect_changes([sample_package])

        # Segunda detección con el mismo paquete
        changes = detector.detect_changes([sample_package])

        assert len(changes["nuevos"]) == 0
        assert len(changes["actualizados"]) == 0
        assert len(changes["eliminados"]) == 0

    def test_multiple_changes(self, detector, sample_package):
        """Probar detección de múltiples cambios."""
        # Primera detección
        package2 = sample_package.model_copy(deep=True)
        package2.data_hash = "def456"
        detector.detect_changes([sample_package, package2])

        # Modificar un paquete y eliminar otro
        updated_package = sample_package.model_copy(deep=True)
        updated_package.precio = 1600.0
        package3 = sample_package.model_copy(deep=True)
        package3.data_hash = "ghi789"

        # Segunda detección
        changes = detector.detect_changes([updated_package, package3])

        assert len(changes["nuevos"]) == 1
        assert len(changes["actualizados"]) == 1
        assert len(changes["eliminados"]) == 1

    def test_price_tolerance(self, detector, sample_package):
        """Probar tolerancia en cambios de precio."""
        # Primera detección
        detector.detect_changes([sample_package])

        # Cambio mínimo en precio (menos de 1 centavo)
        updated_package = sample_package.model_copy(deep=True)
        updated_package.precio = 1500.001

        # No debería detectar cambio
        changes = detector.detect_changes([updated_package])
        assert len(changes["actualizados"]) == 0

        # Cambio significativo
        updated_package.precio = 1500.02
        changes = detector.detect_changes([updated_package])
        assert len(changes["actualizados"]) == 1
