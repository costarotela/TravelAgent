import pytest
from datetime import datetime
from src.core.detector import ChangeDetector
from src.core.providers.ola_models import PaqueteOLA, Vuelo, PoliticasCancelacion


@pytest.fixture
def detector():
    return ChangeDetector(
        update_threshold=2, price_change_threshold=0.1, availability_threshold=0.2
    )


@pytest.fixture
def sample_package():
    return PaqueteOLA(
        id="PKG001",
        destino="Cancún",
        origen="Buenos Aires",
        duracion=7,
        precio=1500.0,
        precio_anterior=1500.0,  # No hay cambio
        impuestos=200.0,
        fechas=[datetime.now()],
        disponibilidad=True,
        disponibilidad_anterior=True,  # No hay cambio
        vuelos=[
            Vuelo(
                salida="10:00",
                llegada="16:00",
                duracion="6h",
                numero_vuelo="AA123",
                aerolinea="American Airlines",
            ),
            Vuelo(
                salida="17:00",
                llegada="23:00",
                duracion="6h",
                numero_vuelo="AA124",
                aerolinea="American Airlines",
            ),
        ],
        aerolinea="American Airlines",
        moneda="USD",
        incluye=["Traslados", "Alojamiento"],
        politicas_cancelacion=PoliticasCancelacion(
            **{
                "0-61 noches antes": "Penalidad 100%",
                "62-90 noches antes": "Penalidad 50%",
                "91+ noches antes": "Sin penalidad",
            }
        ),
    )


def test_detect_significant_changes_by_updates(detector):
    """Prueba la detección de cambios por número de actualizaciones."""
    # Preparar reporte con más actualizaciones que el umbral
    pkg = PaqueteOLA(
        id="PKG001",
        destino="Cancún",
        origen="Buenos Aires",
        duracion=7,
        precio=1500.0,
        precio_anterior=1500.0,  # No hay cambio
        impuestos=200.0,
        fechas=[datetime.now()],
        disponibilidad=True,
        disponibilidad_anterior=True,  # No hay cambio
        vuelos=[
            Vuelo(
                salida="10:00",
                llegada="16:00",
                duracion="6h",
                numero_vuelo="AA123",
                aerolinea="American Airlines",
            ),
            Vuelo(
                salida="17:00",
                llegada="23:00",
                duracion="6h",
                numero_vuelo="AA124",
                aerolinea="American Airlines",
            ),
        ],
        aerolinea="American Airlines",
        moneda="USD",
        incluye=["Traslados", "Alojamiento"],
        politicas_cancelacion=PoliticasCancelacion(
            **{
                "0-61 noches antes": "Penalidad 100%",
                "62-90 noches antes": "Penalidad 50%",
                "91+ noches antes": "Sin penalidad",
            }
        ),
    )

    report = {
        "nuevos": [],
        "actualizados": [pkg, pkg, pkg],  # 3 actualizaciones
        "eliminados": [],
    }

    stats = {"total_nuevos": 0, "total_actualizados": 3, "total_eliminados": 0}

    # Verificar que se detecten cambios significativos
    assert detector._detect_significant_changes(report, stats) is True


def test_detect_significant_changes_by_price(detector, sample_package):
    """Prueba la detección de cambios por variación de precio."""
    # Crear paquete con cambio de precio significativo
    pkg = sample_package
    pkg.precio_anterior = 1500.0
    pkg.precio = 1700.0  # Cambio del 13.33%

    report = {"nuevos": [], "actualizados": [pkg], "eliminados": []}

    stats = {"total_nuevos": 0, "total_actualizados": 1, "total_eliminados": 0}

    # Verificar que se detecten cambios significativos
    assert detector._detect_significant_changes(report, stats) is True


def test_no_significant_changes(detector, sample_package):
    """Prueba cuando no hay cambios significativos."""
    # Crear paquete con cambio de precio menor
    pkg = sample_package
    pkg.precio_anterior = 1500.0
    pkg.precio = 1510.0  # Cambio del 0.67%

    report = {"nuevos": [], "actualizados": [pkg], "eliminados": []}

    stats = {"total_nuevos": 0, "total_actualizados": 1, "total_eliminados": 0}

    # Verificar que no se detecten cambios significativos
    assert detector._detect_significant_changes(report, stats) is False


def test_analyze_report_triggers_actions(detector, sample_package):
    """Prueba que el análisis desencadene acciones cuando corresponde."""
    # Crear paquete con cambios significativos
    pkg = sample_package
    pkg.precio_anterior = 1500.0
    pkg.precio = 1700.0
    pkg.disponibilidad_anterior = True
    pkg.disponibilidad = False

    report = {"nuevos": [], "actualizados": [pkg], "eliminados": []}

    # Analizar reporte
    result = detector.analyze_report(report)

    # Verificar resultados
    assert result["cambios_significativos"] is True
    assert len(result["acciones_requeridas"]) > 0
    assert any(
        accion["tipo"] == "analisis_precios" for accion in result["acciones_requeridas"]
    )
    assert any(
        accion["tipo"] == "alerta_disponibilidad"
        for accion in result["acciones_requeridas"]
    )


def test_analyze_report_with_no_changes(detector):
    """Prueba el análisis cuando no hay cambios significativos."""
    report = {"nuevos": [], "actualizados": [], "eliminados": []}

    # Analizar reporte
    result = detector.analyze_report(report)

    # Verificar resultados
    assert result["cambios_significativos"] is False
    assert len(result["acciones_requeridas"]) == 0
    assert result["total_nuevos"] == 0
    assert result["total_actualizados"] == 0
    assert result["total_eliminados"] == 0
