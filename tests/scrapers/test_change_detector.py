"""
Pruebas para el detector de cambios en paquetes turísticos.
"""

import pytest
from decimal import Decimal
from datetime import datetime
import copy

from agent_core.scrapers.change_detector import ChangeDetector
from agent_core.scrapers.validators import ValidationError


@pytest.fixture
def detector():
    return ChangeDetector()


@pytest.fixture
def base_package():
    return {
        "destino": "Costa Mujeres",
        "aerolinea": "Aerolíneas Argentinas",
        "duracion": "7 noches",
        "precio": Decimal("150000.00"),
        "impuestos": Decimal("25000.00"),
        "incluye": ["Traslados", "Desayuno"],
        "fechas": ["2025-03-15", "2025-03-22"],
        "politicas": [{"periodo": "Hasta 30 días antes", "penalidad": "10% del total"}],
        "assist_card": {
            "cobertura": Decimal("50000.00"),
            "validez": "7 días",
            "territorialidad": "Internacional",
            "limitaciones": "Hasta 70 años",
            "gastos_reserva": Decimal("1500.00"),
        },
    }


def test_detect_no_changes(detector, base_package):
    """Prueba que no se detecten cambios cuando los paquetes son idénticos."""
    changes = detector.detect_changes(base_package, copy.deepcopy(base_package))
    assert not changes
    assert not detector.is_significant_change(changes)


def test_detect_price_change(detector, base_package):
    """Prueba detección de cambios en precio."""
    new_package = copy.deepcopy(base_package)
    new_package["precio"] = Decimal("165000.00")  # 10% más

    changes = detector.detect_changes(base_package, new_package)

    assert "precio" in changes
    assert changes["precio"]["diferencia_porcentual"] == 10
    assert detector.is_significant_change(changes)


def test_detect_availability_change(detector, base_package):
    """Prueba detección de cambios en disponibilidad."""
    new_package = copy.deepcopy(base_package)
    new_package["fechas"] = ["2025-03-15", "2025-03-22", "2025-03-29"]

    changes = detector.detect_changes(base_package, new_package)

    assert "disponibilidad" in changes
    assert len(changes["disponibilidad"]["fechas_agregadas"]) == 1
    assert changes["disponibilidad"]["fechas_agregadas"][0] == "2025-03-29"
    assert detector.is_significant_change(changes)


def test_detect_tax_change(detector, base_package):
    """Prueba detección de cambios en impuestos."""
    new_package = copy.deepcopy(base_package)
    new_package["impuestos"] = Decimal("27500.00")  # 10% más

    changes = detector.detect_changes(base_package, new_package)

    assert "impuestos" in changes
    assert changes["impuestos"]["diferencia_porcentual"] == 10
    assert detector.is_significant_change(changes)


def test_detect_policy_change(detector, base_package):
    """Prueba detección de cambios en políticas."""
    new_package = copy.deepcopy(base_package)
    new_package["politicas"] = [
        {
            "periodo": "Hasta 30 días antes",
            "penalidad": "15% del total",  # Cambio en penalidad
        }
    ]

    changes = detector.detect_changes(base_package, new_package)

    assert "politicas" in changes
    assert detector.is_significant_change(changes)


def test_detect_assist_card_change(detector, base_package):
    """Prueba detección de cambios en Assist Card."""
    new_package = copy.deepcopy(base_package)
    new_package["assist_card"]["cobertura"] = Decimal("60000.00")  # 20% más

    changes = detector.detect_changes(base_package, new_package)

    assert "assist_card" in changes
    assert "cobertura" in changes["assist_card"]
    assert changes["assist_card"]["cobertura"]["diferencia_porcentual"] == 20
    assert detector.is_significant_change(changes)


def test_invalid_data_validation(detector, base_package):
    """Prueba que se validen los datos antes de detectar cambios."""
    invalid_package = copy.deepcopy(base_package)
    invalid_package["precio"] = Decimal("-150000.00")  # Precio negativo

    with pytest.raises(ValidationError):
        detector.detect_changes(base_package, invalid_package)


def test_multiple_changes(detector, base_package):
    """Prueba detección de múltiples cambios simultáneos."""
    new_package = copy.deepcopy(base_package)
    new_package["precio"] = Decimal("165000.00")  # 10% más
    new_package["impuestos"] = Decimal("27500.00")  # 10% más
    new_package["fechas"].append("2025-03-29")  # Nueva fecha

    changes = detector.detect_changes(base_package, new_package)

    assert len(changes) == 3
    assert "precio" in changes
    assert "impuestos" in changes
    assert "disponibilidad" in changes
    assert detector.is_significant_change(changes)


def test_non_significant_changes(detector, base_package):
    """Prueba cambios que no alcanzan el umbral de significancia."""
    new_package = copy.deepcopy(base_package)
    new_package["precio"] = Decimal("151500.00")  # 1% más
    new_package["impuestos"] = Decimal("25250.00")  # 1% más

    changes = detector.detect_changes(base_package, new_package)

    assert len(changes) == 2
    assert not detector.is_significant_change(changes)
