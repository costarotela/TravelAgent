"""Tests de integración para el sistema OLA."""

import pytest
import asyncio
from datetime import datetime
from src.core.providers.ola import OLAProvider
from src.core.monitoring.ola_monitor import OLAMonitor
from src.core.providers.ola_dynamic_updater import OLAUpdater


@pytest.fixture
def config():
    """Fixture para configuración de prueba."""
    return {
        "base_url": "https://test-ola.com",
        "headless": True,
        "cache_size": 100,
        "cache_ttl": 3600,
        "monitor_port": 9090,
    }


@pytest.fixture
async def monitor(config):
    """Fixture para monitor."""
    monitor = OLAMonitor(port=config["monitor_port"])
    yield monitor
    # Cleanup


@pytest.fixture
async def updater(config, monitor):
    """Fixture para actualizador."""
    updater = OLAUpdater(config, monitor=monitor)
    yield updater
    # Cleanup


@pytest.fixture
async def provider(config):
    """Fixture para proveedor OLA."""
    provider = OLAProvider(config)
    yield provider
    await provider.close()


@pytest.mark.integration
@pytest.mark.asyncio
class TestOLAIntegration:
    """Suite de pruebas de integración para OLA."""

    async def test_full_update_flow(self, provider, updater, monitor):
        """Probar flujo completo de actualización."""
        destino = "Cancún"

        # 1. Obtener datos iniciales
        initial_data = await provider.search_packages(
            {
                "destino": destino,
                "fecha_inicio": "2025-03-01",
                "fecha_fin": "2025-03-31",
            }
        )

        # 2. Realizar actualización
        update_result = await updater.fetch_data(destino)

        # 3. Obtener datos actualizados
        updated_data = await provider.search_packages(
            {
                "destino": destino,
                "fecha_inicio": "2025-03-01",
                "fecha_fin": "2025-03-31",
            }
        )

        # Verificaciones
        assert len(updated_data) >= len(initial_data)
        assert update_result["stats"]["total_nuevos"] >= 0

        # Verificar métricas
        metrics = await self._get_metrics(monitor)
        assert metrics["paquetes_nuevos"] >= 0
        assert metrics["tiempo_actualizacion"] > 0

    async def test_concurrent_updates(self, provider, updater, monitor):
        """Probar actualizaciones concurrentes."""
        destinos = ["Cancún", "Miami", "Madrid"]

        # Ejecutar actualizaciones concurrentes
        tasks = [updater.fetch_data(destino) for destino in destinos]
        results = await asyncio.gather(*tasks)

        # Verificar resultados
        for result in results:
            assert "stats" in result
            assert "details" in result

        # Verificar métricas
        metrics = await self._get_metrics(monitor)
        assert metrics["error_counter"] == 0  # No errores
        assert metrics["scraping_duration"] > 0

    async def test_error_recovery(self, provider, updater, monitor):
        """Probar recuperación de errores."""
        # 1. Forzar error cambiando URL
        updater.base_url = "https://invalid-url"

        # 2. Intentar actualización
        with pytest.raises(Exception):
            await updater.fetch_data("Cancún")

        # 3. Verificar métricas de error
        metrics = await self._get_metrics(monitor)
        assert metrics["error_counter"] > 0

        # 4. Restaurar URL y verificar recuperación
        updater.base_url = "https://test-ola.com"
        result = await updater.fetch_data("Cancún")
        assert result["stats"]["total_nuevos"] >= 0

    async def test_cache_behavior(self, provider, updater):
        """Probar comportamiento del caché."""
        destino = "Cancún"

        # 1. Primera actualización
        result1 = await updater.fetch_data(destino)
        cache_size1 = len(updater.cache)

        # 2. Segunda actualización inmediata
        result2 = await updater.fetch_data(destino)
        cache_size2 = len(updater.cache)

        # Verificar que el caché se mantiene consistente
        assert cache_size2 >= cache_size1
        assert result2["stats"]["total_nuevos"] <= result1["stats"]["total_nuevos"]

    async def test_data_consistency(self, provider, updater):
        """Probar consistencia de datos."""
        destino = "Cancún"

        # 1. Obtener datos vía updater
        update_result = await updater.fetch_data(destino)

        # 2. Obtener datos vía provider
        provider_data = await provider.search_packages({"destino": destino})

        # 3. Verificar consistencia
        cached_hashes = set(updater.cache.keys())
        provider_hashes = {pkg.data_hash for pkg in provider_data}

        # Debe haber intersección entre los conjuntos
        assert cached_hashes.intersection(provider_hashes)

        # Verificar datos específicos
        for pkg in provider_data:
            if pkg.data_hash in updater.cache:
                cached_pkg = updater.cache[pkg.data_hash]
                assert pkg.precio == cached_pkg.precio
                assert pkg.destino == cached_pkg.destino

    async def _get_metrics(self, monitor):
        """Obtener métricas del monitor."""
        # Simular recolección de métricas
        return {
            "paquetes_nuevos": monitor.paquetes_nuevos._value.get(),
            "tiempo_actualizacion": monitor.tiempo_actualizacion._value.get(),
            "error_counter": monitor.error_counter._value.get(),
            "scraping_duration": monitor.scraping_duration._value.get(),
        }
