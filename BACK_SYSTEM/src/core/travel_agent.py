import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from prometheus_client import Counter, Histogram

from .providers.ola_dynamic_updater import OLADynamicUpdater
from .providers.ola_models import PaqueteOLA
from .detector import ChangeDetector
from .cache.smart_cache import SmartCache
from ..utils.monitoring import setup_monitoring

# Métricas
UPDATES_TOTAL = Counter(
    "travel_agent_updates_total", "Total number of updates performed"
)
UPDATE_DURATION = Histogram(
    "travel_agent_update_duration_seconds", "Time spent updating data"
)

logger = logging.getLogger(__name__)


class TravelAgent:
    """
    Agente principal que coordina actualizaciones y detección de cambios.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializa el agente.

        Args:
            config: Configuración opcional
        """
        self.config = config or {
            "update_interval": 3600,  # 1 hora
            "update_threshold": 5,
            "price_change_threshold": 0.1,  # 10%
            "availability_threshold": 0.2,  # 20%
            "cache_ttl": 300,  # 5 minutos
        }

        # Componentes
        self.updater = OLADynamicUpdater(self.config)
        self.detector = ChangeDetector(
            update_threshold=self.config["update_threshold"],
            price_change_threshold=self.config["price_change_threshold"],
            availability_threshold=self.config["availability_threshold"],
        )
        self.cache = SmartCache(default_ttl=self.config["cache_ttl"])

        # Configuración
        setup_monitoring()

    async def update_data(self, destino: str) -> Dict[str, any]:
        """
        Actualiza datos para un destino.

        Args:
            destino: Destino a actualizar

        Returns:
            Diccionario con resultados de la actualización
        """
        start_time = datetime.now()

        try:
            # Buscar en caché
            cache_key = f"update_data_{destino}"
            cached_data = self.cache.get(cache_key)

            if cached_data:
                logger.info(f"Datos encontrados en caché para {destino}")
                return cached_data

            # Obtener actualizaciones
            changes = await self.updater.update_packages()

            # Analizar cambios
            analysis = self.detector.analyze_report(changes)

            # Preparar resultado
            result = {
                "cambios": changes,
                "analisis": analysis,
                "timestamp": datetime.now().isoformat(),
            }

            # Actualizar caché
            self.cache.set(cache_key, result)

            # Registrar métricas
            UPDATES_TOTAL.inc()
            duration = (datetime.now() - start_time).total_seconds()
            UPDATE_DURATION.observe(duration)

            # Loguear resultado
            self._log_update_result(result, duration)

            return result

        except Exception as e:
            logger.error(f"Error actualizando datos para {destino}: {str(e)}")
            raise

    def _log_update_result(self, result: Dict[str, any], duration: float):
        """
        Registra el resultado de la actualización.

        Args:
            result: Resultado de la actualización
            duration: Duración de la actualización
        """
        analysis = result["analisis"]
        changes = result["cambios"]

        logger.info(
            f"Actualización completada en {duration:.2f}s\n"
            f"Nuevos: {len(changes.get('nuevos', []))}\n"
            f"Actualizados: {len(changes.get('actualizados', []))}\n"
            f"Eliminados: {len(changes.get('eliminados', []))}\n"
            f"Cambios significativos: {analysis['cambios_significativos']}\n"
            f"Acciones requeridas: {len(analysis['acciones_requeridas'])}"
        )

    async def start_periodic_updates(self):
        """Inicia actualizaciones periódicas."""
        logger.info(
            f"Iniciando actualizaciones periódicas cada "
            f"{self.config['update_interval']}s"
        )

        while True:
            try:
                await self.update_data("all")  # Actualizar todos los destinos
            except Exception as e:
                logger.error(f"Error en actualización periódica: {str(e)}")

            await asyncio.sleep(self.config["update_interval"])


async def main():
    """Función principal de ejemplo."""
    agent = TravelAgent()

    # Ejemplo de actualización única
    result = await agent.update_data("Cancún")

    # Iniciar actualizaciones periódicas
    await agent.start_periodic_updates()


if __name__ == "__main__":
    asyncio.run(main())
