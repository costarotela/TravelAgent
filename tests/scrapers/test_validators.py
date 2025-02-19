"""
Pruebas para el módulo de validación de datos.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from agent_core.scrapers.validators import DataValidator, ValidationError

@pytest.fixture
def validator():
    return DataValidator()

def test_validate_package_success(validator):
    """Prueba validación exitosa de paquete."""
    package_data = {
        'destino': 'Costa Mujeres',
        'aerolinea': 'Aerolíneas Argentinas',
        'duracion': '7 noches',
        'precio': Decimal('150000.00'),
        'impuestos': Decimal('25000.00'),
        'incluye': ['Traslados', 'Desayuno'],
        'fechas': ['2025-03-15', '2025-03-22']
    }
    validator.validate_package(package_data)  # No debe levantar excepción

def test_validate_package_missing_field(validator):
    """Prueba validación de paquete con campo faltante."""
    package_data = {
        'destino': 'Costa Mujeres',
        'aerolinea': 'Aerolíneas Argentinas',
        'duracion': '7 noches',
        'precio': Decimal('150000.00'),
        # 'impuestos' faltante
        'incluye': ['Traslados', 'Desayuno'],
        'fechas': ['2025-03-15', '2025-03-22']
    }
    with pytest.raises(ValidationError, match="Campo requerido faltante: impuestos"):
        validator.validate_package(package_data)

def test_validate_package_invalid_price(validator):
    """Prueba validación de paquete con precio inválido."""
    package_data = {
        'destino': 'Costa Mujeres',
        'aerolinea': 'Aerolíneas Argentinas',
        'duracion': '7 noches',
        'precio': Decimal('-150000.00'),  # Precio negativo
        'impuestos': Decimal('25000.00'),
        'incluye': ['Traslados', 'Desayuno'],
        'fechas': ['2025-03-15', '2025-03-22']
    }
    with pytest.raises(ValidationError, match="Precio inválido"):
        validator.validate_package(package_data)

def test_validate_flight_success(validator):
    """Prueba validación exitosa de vuelo."""
    flight_data = {
        'salida': '2025-03-15 10:00',
        'llegada': '2025-03-15 12:00',
        'duracion': '2 horas',
        'escalas': [
            {
                'ubicacion': 'Panama',
                'tiempo_espera': '1 hora'
            }
        ]
    }
    validator.validate_flight(flight_data)  # No debe levantar excepción

def test_validate_flight_missing_field(validator):
    """Prueba validación de vuelo con campo faltante."""
    flight_data = {
        'salida': '2025-03-15 10:00',
        # 'llegada' faltante
        'duracion': '2 horas'
    }
    with pytest.raises(ValidationError, match="Campo de vuelo requerido faltante: llegada"):
        validator.validate_flight(flight_data)

def test_validate_cancellation_policies_success(validator):
    """Prueba validación exitosa de políticas de cancelación."""
    policies = [
        {
            'periodo': 'Hasta 30 días antes',
            'penalidad': '10% del total'
        },
        {
            'periodo': 'Entre 29 y 15 días antes',
            'penalidad': '25% del total'
        }
    ]
    validator.validate_cancellation_policies(policies)  # No debe levantar excepción

def test_validate_cancellation_policies_invalid(validator):
    """Prueba validación de políticas de cancelación inválidas."""
    policies = [
        {
            'periodo': 'Hasta 30 días antes',
            # 'penalidad' faltante
        }
    ]
    with pytest.raises(ValidationError, match="Política debe tener periodo y penalidad"):
        validator.validate_cancellation_policies(policies)

def test_validate_assist_card_success(validator):
    """Prueba validación exitosa de Assist Card."""
    assist_data = {
        'cobertura': Decimal('150000.00'),
        'validez': '7 días',
        'territorialidad': 'Internacional',
        'limitaciones': 'Hasta 70 años',
        'gastos_reserva': Decimal('1500.00')
    }
    validator.validate_assist_card(assist_data)  # No debe levantar excepción

def test_validate_assist_card_invalid_coverage(validator):
    """Prueba validación de Assist Card con cobertura inválida."""
    assist_data = {
        'cobertura': Decimal('-150000.00'),  # Cobertura negativa
        'validez': '7 días',
        'territorialidad': 'Internacional',
        'limitaciones': 'Hasta 70 años',
        'gastos_reserva': Decimal('1500.00')
    }
    with pytest.raises(ValidationError, match="Cobertura inválida"):
        validator.validate_assist_card(assist_data)

def test_validate_special_taxes_success(validator):
    """Prueba validación exitosa de impuestos especiales."""
    taxes = [
        {
            'nombre': 'IVA',
            'monto': Decimal('21000.00'),
            'detalle': '21% sobre el total'
        },
        {
            'nombre': 'Tasa aeroportuaria',
            'monto': Decimal('5000.00'),
            'detalle': 'Cargo fijo por pasajero'
        }
    ]
    validator.validate_special_taxes(taxes)  # No debe levantar excepción

def test_validate_special_taxes_invalid(validator):
    """Prueba validación de impuestos especiales inválidos."""
    taxes = [
        {
            'nombre': 'IVA',
            'monto': Decimal('-21000.00'),  # Monto negativo
            'detalle': '21% sobre el total'
        }
    ]
    with pytest.raises(ValidationError, match="Monto de impuesto inválido"):
        validator.validate_special_taxes(taxes)

def test_validate_search_criteria_success(validator):
    """Prueba validación exitosa de criterios de búsqueda."""
    criteria = {
        'destino': 'Costa Mujeres',
        'fechas': ['2025-03-15', '2025-03-22']
    }
    validator.validate_search_criteria(criteria)  # No debe levantar excepción

def test_validate_search_criteria_invalid_dates(validator):
    """Prueba validación de criterios con fechas inválidas."""
    criteria = {
        'destino': 'Costa Mujeres',
        'fechas': ['2025-03-15', 'fecha_invalida']  # Fecha inválida
    }
    with pytest.raises(ValidationError, match="Fecha inválida: fecha_invalida"):
        validator.validate_search_criteria(criteria)
