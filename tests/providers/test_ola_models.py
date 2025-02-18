"""Tests para los modelos de datos OLA."""

import pytest
from datetime import datetime
from src.core.providers.ola_models import (
    Vuelo,
    ImpuestoEspecial,
    PoliticasCancelacion,
    PaqueteOLA,
)


@pytest.fixture
def vuelo_data():
    """Fixture para datos de vuelo."""
    return {
        "salida": "08:00",
        "llegada": "10:00",
        "duracion": "2h",
        "aerolinea": "AeroMéxico",
        "escala": None,
        "espera": None,
    }


@pytest.fixture
def impuesto_data():
    """Fixture para datos de impuesto."""
    return {"nombre": "IVA", "monto": 100.0, "detalle": "Impuesto al valor agregado"}


@pytest.fixture
def politicas_data():
    """Fixture para datos de políticas."""
    return {
        "0-61 noches antes": "Reembolso completo",
        "62-90 noches antes": "50% reembolso",
        "91+ noches antes": "No reembolsable",
    }


@pytest.fixture
def paquete_data(vuelo_data, politicas_data):
    """Fixture para datos de paquete."""
    return {
        "destino": "Cancún",
        "origen": "Buenos Aires",
        "duracion": 7,
        "vuelos": [vuelo_data],
        "aerolinea": "AeroMéxico",
        "moneda": "USD",
        "precio": 1500.0,
        "impuestos": 200.0,
        "fechas": [datetime.now()],
        "incluye": ["Vuelo", "Hotel", "Traslados"],
        "politicas_cancelacion": politicas_data,
        "disponibilidad": True,
    }


class TestVuelo:
    """Suite de pruebas para modelo Vuelo."""

    def test_vuelo_creation(self, vuelo_data):
        """Probar creación de vuelo."""
        vuelo = Vuelo(**vuelo_data)
        assert vuelo.salida == vuelo_data["salida"]
        assert vuelo.llegada == vuelo_data["llegada"]
        assert vuelo.duracion == vuelo_data["duracion"]
        assert vuelo.aerolinea == vuelo_data["aerolinea"]

    def test_vuelo_optional_fields(self, vuelo_data):
        """Probar campos opcionales de vuelo."""
        vuelo = Vuelo(**vuelo_data)
        assert vuelo.escala is None
        assert vuelo.espera is None

    def test_vuelo_validation(self):
        """Probar validación de campos requeridos."""
        with pytest.raises(ValueError):
            Vuelo(salida="08:00")  # Faltan campos requeridos


class TestImpuestoEspecial:
    """Suite de pruebas para modelo ImpuestoEspecial."""

    def test_impuesto_creation(self, impuesto_data):
        """Probar creación de impuesto."""
        impuesto = ImpuestoEspecial(**impuesto_data)
        assert impuesto.nombre == impuesto_data["nombre"]
        assert impuesto.monto == impuesto_data["monto"]
        assert impuesto.detalle == impuesto_data["detalle"]

    def test_impuesto_optional_fields(self):
        """Probar campos opcionales de impuesto."""
        impuesto = ImpuestoEspecial(nombre="Tasa", monto=50.0)
        assert impuesto.detalle is None


class TestPoliticasCancelacion:
    """Suite de pruebas para modelo PoliticasCancelacion."""

    def test_politicas_creation(self, politicas_data):
        """Probar creación de políticas."""
        politicas = PoliticasCancelacion(**politicas_data)
        assert politicas.periodo_61_noches == politicas_data["0-61 noches antes"]
        assert politicas.periodo_62_90 == politicas_data["62-90 noches antes"]
        assert politicas.periodo_91_plus == politicas_data["91+ noches antes"]

    def test_politicas_validation(self):
        """Probar validación de campos requeridos."""
        with pytest.raises(ValueError):
            PoliticasCancelacion(
                **{
                    "0-61 noches antes": "Reembolso"
                    # Faltan campos requeridos
                }
            )


class TestPaqueteOLA:
    """Suite de pruebas para modelo PaqueteOLA."""

    def test_paquete_creation(self, paquete_data):
        """Probar creación de paquete."""
        paquete = PaqueteOLA(**paquete_data)
        assert paquete.destino == paquete_data["destino"]
        assert paquete.origen == paquete_data["origen"]
        assert paquete.duracion == paquete_data["duracion"]
        assert len(paquete.vuelos) == 1
        assert paquete.precio == paquete_data["precio"]

    def test_paquete_validation(self, paquete_data):
        """Probar validación de campos."""
        # Precio negativo
        invalid_data = paquete_data.copy()
        invalid_data["precio"] = -100
        with pytest.raises(ValueError):
            PaqueteOLA(**invalid_data)

        # Duración inválida
        invalid_data = paquete_data.copy()
        invalid_data["duracion"] = 0
        with pytest.raises(ValueError):
            PaqueteOLA(**invalid_data)

    def test_paquete_optional_fields(self, paquete_data):
        """Probar campos opcionales."""
        paquete = PaqueteOLA(**paquete_data)
        assert paquete.assist_card is None
        assert paquete.restricciones is None
        assert paquete.data_hash is None
