"""Actualizador dinámico para datos de OLA."""

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from src.core.browsers.smart_browser import SmartBrowser
from src.core.monitoring.ola_monitor import OLAMonitor
from src.core.providers.ola_models import PaqueteOLA
from src.core.providers.ola_change_detector import OLAChangeDetector
from prometheus_client import Counter, Histogram

# Métricas de monitoreo
UPDATES_TOTAL = Counter("ola_updates_total", "Total number of OLA updates performed")
UPDATE_DURATION = Histogram(
    "ola_update_duration_seconds", "Time spent updating OLA packages"
)
CHANGES_DETECTED = Counter(
    "ola_changes_detected", "Number of changes detected in OLA packages"
)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OLADynamicUpdater:
    """Actualizador dinámico para datos de OLA."""

    def __init__(self, config: Dict, monitor: Optional[OLAMonitor] = None):
        """
        Inicializa el actualizador.

        Args:
            config: Configuración del actualizador
            monitor: Monitor de métricas (opcional)
        """
        self.config = config
        self.browser = SmartBrowser(
            headless=config.get("headless", True),
            proxy=config.get("proxy"),
            user_agent=config.get("user_agent"),
        )
        self.base_url = config.get("base_url", "https://ola.com")
        self.monitor = monitor
        self.change_detector = OLAChangeDetector()

        # Configurar timeouts
        self.timeout = {
            "navigation": config.get("timeout_navigation", 30),
            "element": config.get("timeout_element", 10),
            "script": config.get("timeout_script", 20),
        }

    async def fetch_data(self, destino: str) -> Dict:
        """
        Obtiene y procesa datos actualizados para un destino.

        Args:
            destino: Destino a actualizar

        Returns:
            Dict con estadísticas y detalles de la actualización
        """
        start_time = datetime.now()
        try:
            # 1. Obtener datos crudos
            raw_data = await self._scrape_data(destino)

            # 2. Normalizar datos
            normalized_data = self._normalize_data(raw_data)

            # 3. Detectar cambios
            changes = self.change_detector.detect_changes(normalized_data)

            # 4. Analizar cambios
            stats = self.change_detector.analyze_changes(changes)

            # 5. Actualizar métricas
            if self.monitor:
                self._update_metrics(stats, destino, start_time)

            return {"stats": stats, "details": changes}

        except Exception as e:
            self._log_error(f"Error en fetch_data: {str(e)}", destino)
            raise

    async def _scrape_data(self, destino: str) -> List[Dict]:
        """
        Extrae datos crudos del sitio web.

        Args:
            destino: Destino a buscar

        Returns:
            Lista de diccionarios con datos crudos
        """
        try:
            url = f"{self.base_url}/busqueda?destino={destino}"

            async with self.browser as browser:
                # 1. Navegar a la página
                await browser.navigate(url)

                # 2. Esperar elementos principales
                await browser.wait_for_element(
                    ".paquete-container", timeout=self.timeout["element"]
                )

                # 3. Extraer datos
                script = """
                () => {
                    const paquetes = [];
                    document.querySelectorAll('.paquete-item').forEach(item => {
                        const paquete = {
                            destino: item.querySelector('.destino')?.textContent,
                            precio: item.querySelector('.precio')?.textContent,
                            aerolinea: item.querySelector('.aerolinea')?.textContent,
                            duracion: item.querySelector('.duracion')?.textContent,
                            incluye: Array.from(
                                item.querySelectorAll('.servicios-incluidos li'),
                                el => el.textContent
                            ),
                            vuelos: Array.from(
                                item.querySelectorAll('.vuelos-info .vuelo'),
                                vuelo => ({
                                    salida: vuelo.querySelector('.hora-salida')?.textContent,
                                    llegada: vuelo.querySelector('.hora-llegada')?.textContent,
                                    duracion: vuelo.querySelector('.duracion')?.textContent,
                                    aerolinea: vuelo.querySelector('.aerolinea')?.textContent
                                })
                            ),
                            politicas_cancelacion: {
                                "0-61 noches antes": item.querySelector('.periodo-1')?.textContent,
                                "62-90 noches antes": item.querySelector('.periodo-2')?.textContent,
                                "91+ noches antes": item.querySelector('.periodo-3')?.textContent
                            }
                        };
                        paquetes.push(paquete);
                    });
                    return paquetes;
                }
                """
                data = await browser.execute_script(script)
                return data

        except Exception as e:
            self._log_error(f"Error en _scrape_data: {str(e)}", destino)
            raise

    def _normalize_data(self, raw_data: List[Dict]) -> List[PaqueteOLA]:
        """
        Normaliza y valida datos crudos.

        Args:
            raw_data: Lista de diccionarios con datos crudos

        Returns:
            Lista de objetos PaqueteOLA validados
        """
        validated = []
        for item in raw_data:
            try:
                # Limpiar y convertir datos
                item["precio"] = float(item["precio"].replace("$", "").replace(",", ""))
                item["duracion"] = int(item["duracion"].replace(" días", ""))
                item["moneda"] = "USD"  # Por defecto
                item["origen"] = "Buenos Aires"  # Por defecto
                item["impuestos"] = item["precio"] * 0.21  # IVA por defecto

                # Generar hash único
                item["data_hash"] = self._generate_hash(item)

                # Crear y validar objeto
                paquete = PaqueteOLA(**item)
                validated.append(paquete)

            except Exception as e:
                self._log_error(f"Error normalizando paquete: {str(e)}")
                continue

        return validated

    def _generate_hash(self, data: Dict) -> str:
        """
        Genera un hash único para un paquete.

        Args:
            data: Datos del paquete

        Returns:
            String con el hash
        """
        # Campos relevantes para el hash
        relevant_fields = ["destino", "aerolinea", "origen", "duracion", "precio"]

        # Crear string para hash
        hash_str = "|".join(str(data.get(field, "")) for field in relevant_fields)

        # Generar hash
        return hashlib.md5(hash_str.encode()).hexdigest()

    def _update_metrics(self, stats: Dict, destino: str, start_time: datetime) -> None:
        """
        Actualiza métricas en el monitor.

        Args:
            stats: Estadísticas de la actualización
            destino: Destino actualizado
            start_time: Tiempo de inicio
        """
        if not self.monitor:
            return

        # Actualizar métricas de paquetes
        self.monitor.update_package_metrics(stats, destino)

        # Actualizar métricas de precios
        price_stats = stats["detalles"]["precio"]
        if price_stats["total_cambios"] > 0:
            changes = price_stats["cambios"]
            price_metrics = {
                "precio_promedio": sum(c["precio_actual"] for c in changes)
                / len(changes),
                "precio_minimo": min(c["precio_actual"] for c in changes),
                "precio_maximo": max(c["precio_actual"] for c in changes),
            }
            self.monitor.update_price_metrics(price_metrics, destino, "USD")

        # Actualizar métricas de rendimiento
        duration = (datetime.now() - start_time).total_seconds()
        self.monitor.update_performance_metrics(duration, destino)

        # Actualizar métricas de disponibilidad
        availability = stats["detalles"]["disponibilidad"]
        self.monitor.update_availability(availability["porcentaje_disponible"], destino)

        # Actualizar métricas de cambios
        UPDATES_TOTAL.inc()
        if stats["detalles"]["cambios"]:
            CHANGES_DETECTED.inc(len(stats["detalles"]["cambios"]))
        UPDATE_DURATION.observe(duration)

    def _log_error(self, message: str, destino: str = None) -> None:
        """
        Registra un error y actualiza métricas.

        Args:
            message: Mensaje de error
            destino: Destino relacionado (opcional)
        """
        error_context = f" para {destino}" if destino else ""
        logger.error(f"{message}{error_context}")

        if self.monitor:
            self.monitor.log_error()
