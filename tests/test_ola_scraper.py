"""
Pruebas para el scraper de OLA y sus componentes.
"""

import pytest
import asyncio
from datetime import datetime
from decimal import Decimal

from agent_core.scrapers.ola_scraper import OlaScraper
from agent_core.scrapers.base import ScraperConfig, Credentials
from agent_core.scrapers.session_manager import SessionManager
from agent_core.scrapers.change_detector import ChangeDetector
from agent_core.schemas.travel import (
    PaqueteOLA,
    VueloDetallado,
    PoliticasCancelacion,
    CotizacionEspecial,
    ImpuestoLocal,
    AssistCard,
)


@pytest.fixture
def sample_package():
    """Paquete de ejemplo para pruebas."""
    return PaqueteOLA(
        destino="Costa Mujeres",
        aerolinea="Avianca",
        origen="Buenos Aires",
        duracion=9,
        moneda="USD",
        incluye=["Aéreo Buenos Aires / Cancún / Buenos Aires", "Traslados en destino"],
        fechas=["02-03-2025", "25-03-2025"],
        precio=3410.0,
        impuestos=1316.91,
        politicas_cancelacion=PoliticasCancelacion(
            **{
                "0-61 noches antes": "100%",
                "62-90 noches antes": "30%",
                "91+ noches antes": "Sin penalización",
            }
        ),
        vuelos=[
            VueloDetallado(
                salida="AEP 02 dom - 04:30",
                escala="LIM 02 dom - 07:40",
                espera="02:10 hs",
                duracion="03:10 hs",
            )
        ],
    )


@pytest.fixture
def modified_package(sample_package):
    """Paquete modificado para pruebas de cambios."""
    modified = sample_package.copy(deep=True)
    modified.precio = 3600.0  # Cambio significativo en precio
    modified.fechas = ["25-03-2025"]  # Cambio en disponibilidad
    return modified


@pytest.fixture
def test_credentials():
    """Credenciales de prueba."""
    return Credentials(username="test_user", password="test_pass")


@pytest.mark.asyncio
async def test_session_manager():
    """Prueba el manejo de sesiones."""
    session_manager = SessionManager(
        min_delay=0.1, max_delay=0.2, max_retries=2  # Delays cortos para pruebas
    )

    # Probar rotación de User Agents
    config1 = await session_manager.get_session_config()
    config2 = await session_manager.get_session_config()
    assert config1["user_agent"] != config2["user_agent"], "User Agent no está rotando"

    # Probar manejo de errores
    error = Exception("Test error")
    should_retry = await session_manager.handle_error(error)
    assert should_retry, "Primer error debería permitir retry"

    # Probar límite de reintentos
    await session_manager.handle_error(error)
    should_retry = await session_manager.handle_error(error)
    assert not should_retry, "Después de max_retries no debería permitir más intentos"


def test_change_detector(sample_package, modified_package):
    """Prueba la detección de cambios."""
    detector = ChangeDetector()

    # Detectar cambios
    changes = detector.detect_changes(sample_package, modified_package)

    # Verificar cambios detectados
    assert "precio" in changes, "No se detectó cambio de precio"
    assert changes["precio"]["diferencia"] == 190.0

    assert "disponibilidad" in changes, "No se detectó cambio en disponibilidad"
    assert len(changes["disponibilidad"]["fechas_removidas"]) == 1

    # Verificar significancia
    assert detector.is_significant_change(
        changes
    ), "Cambios deberían ser significativos"


@pytest.mark.asyncio
async def test_ola_scraper(test_credentials):
    """Prueba el scraper completo."""
    config = ScraperConfig(
        base_url="https://ola.com.ar",
        headless=True,
        login_required=True,
        credentials=test_credentials,
    )

    scraper = OlaScraper(config)

    try:
        # Probar login
        login_success = await scraper.login()
        assert login_success is False, "Login debería fallar con credenciales de prueba"

        # Probar extracción de datos
        packages = await scraper.search_packages({})

        # Verificar estructura básica
        assert isinstance(packages, list), "Debe retornar una lista"
        if packages:  # Si hay resultados
            package = packages[0]
            assert isinstance(package, PaqueteOLA), "Debe ser instancia de PaqueteOLA"
            assert package.destino, "Debe tener destino"
            assert package.precio > 0, "Debe tener precio válido"
            assert isinstance(package.vuelos, list), "Debe tener lista de vuelos"

    except Exception as e:
        pytest.fail(f"Error en scraper: {e}")

    finally:
        await scraper.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
