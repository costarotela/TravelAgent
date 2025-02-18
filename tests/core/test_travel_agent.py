import pytest
from datetime import datetime
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.core.travel_agent import TravelAgent
from src.core.providers.ola_models import PaqueteOLA, Vuelo, PoliticasCancelacion


@pytest.fixture
def config():
    return {
        "update_interval": 60,
        "update_threshold": 2,
        "price_change_threshold": 0.1,
        "availability_threshold": 0.2,
        "cache_ttl": 30,
    }


@pytest.fixture
def sample_changes():
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

    return {"nuevos": [], "actualizados": [pkg], "eliminados": []}


@pytest.mark.asyncio
async def test_update_data_success(config, sample_changes):
    """Prueba una actualización exitosa de datos."""
    # Crear mocks
    mock_updater = AsyncMock()
    mock_updater.update_packages.return_value = sample_changes

    # Crear agente con mocks
    with patch("src.core.travel_agent.OLADynamicUpdater", return_value=mock_updater):
        agent = TravelAgent(config)

        # Ejecutar actualización
        result = await agent.update_data("Cancún")

        # Verificar resultado
        assert "cambios" in result
        assert "analisis" in result
        assert "timestamp" in result
        assert result["cambios"] == sample_changes
        assert not result["analisis"]["cambios_significativos"]


@pytest.mark.asyncio
async def test_update_data_with_cache(config, sample_changes):
    """Prueba el uso de caché en actualizaciones."""
    # Crear mocks
    mock_updater = AsyncMock()
    mock_updater.update_packages.return_value = sample_changes

    # Crear agente con mocks
    with patch("src.core.travel_agent.OLADynamicUpdater", return_value=mock_updater):
        agent = TravelAgent(config)

        # Primera actualización
        result1 = await agent.update_data("Cancún")

        # Segunda actualización (debería usar caché)
        result2 = await agent.update_data("Cancún")

        # Verificar que los resultados son iguales
        assert result1 == result2
        # Verificar que el updater solo se llamó una vez
        assert mock_updater.update_packages.call_count == 1


@pytest.mark.asyncio
async def test_update_data_with_significant_changes(config):
    """Prueba la detección de cambios significativos."""
    # Crear paquete con cambios significativos
    pkg = PaqueteOLA(
        id="PKG001",
        destino="Cancún",
        origen="Buenos Aires",
        duracion=7,
        precio=1700.0,
        precio_anterior=1500.0,
        impuestos=200.0,
        fechas=[datetime.now()],
        disponibilidad=False,
        disponibilidad_anterior=True,
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

    changes = {
        "nuevos": [],
        "actualizados": [pkg, pkg, pkg],  # Más que el umbral
        "eliminados": [],
    }

    # Crear mocks
    mock_updater = AsyncMock()
    mock_updater.update_packages.return_value = changes

    # Crear agente con mocks
    with patch("src.core.travel_agent.OLADynamicUpdater", return_value=mock_updater):
        agent = TravelAgent(config)

        # Ejecutar actualización
        result = await agent.update_data("Cancún")

        # Verificar resultado
        assert result["analisis"]["cambios_significativos"]
        assert len(result["analisis"]["acciones_requeridas"]) > 0


@pytest.mark.asyncio
async def test_periodic_updates(config, sample_changes):
    """Prueba las actualizaciones periódicas."""
    # Crear mocks
    mock_updater = AsyncMock()
    mock_updater.update_packages.return_value = sample_changes

    # Crear agente con mocks
    with patch("src.core.travel_agent.OLADynamicUpdater", return_value=mock_updater):
        agent = TravelAgent(config)

        # Crear tarea de actualización
        update_task = asyncio.create_task(agent.start_periodic_updates())

        # Esperar un poco
        await asyncio.sleep(0.1)

        # Cancelar tarea
        update_task.cancel()

        try:
            await update_task
        except asyncio.CancelledError:
            pass

        # Verificar que se realizó al menos una actualización
        assert mock_updater.update_packages.call_count >= 1


@pytest.mark.asyncio
async def test_update_data_error_handling(config):
    """Prueba el manejo de errores en actualizaciones."""
    # Crear mock que lanza error
    mock_updater = AsyncMock()
    mock_updater.update_packages.side_effect = Exception("Error de prueba")

    # Crear agente con mock
    with patch("src.core.travel_agent.OLADynamicUpdater", return_value=mock_updater):
        agent = TravelAgent(config)

        # Verificar que se maneja el error
        with pytest.raises(Exception) as exc_info:
            await agent.update_data("Cancún")

        assert str(exc_info.value) == "Error de prueba"
