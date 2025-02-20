"""
Motor de scraping.

Este módulo implementa:
1. Extracción de datos
2. Parseo de contenido
3. Validación de datos
4. Control de errores
"""

from typing import Dict, Any, Optional, List, Type
from datetime import datetime
import logging
import asyncio
from abc import ABC, abstractmethod
from prometheus_client import Counter, Histogram
import aiohttp
from bs4 import BeautifulSoup

from ...schemas import ScrapingConfig, ScrapingResult, DataValidator, ExtractorRule
from ...metrics import get_metrics_collector
from ..base_collector import BaseCollector
from ..browser_automation.browser_manager import get_browser_manager

# Métricas
SCRAPING_OPERATIONS = Counter(
    "scraping_operations_total",
    "Number of scraping operations",
    ["scraper_type", "status"],
)

SCRAPING_LATENCY = Histogram(
    "scraping_operation_latency_seconds",
    "Latency of scraping operations",
    ["scraper_type"],
)


class BaseScraper(ABC):
    """
    Scraper base.

    Responsabilidades:
    1. Definir interfaz común
    2. Extraer datos
    3. Validar resultados
    """

    def __init__(self, config: Optional[ScrapingConfig] = None):
        """
        Inicializar scraper.

        Args:
            config: Configuración de scraping
        """
        self.logger = logging.getLogger(__name__)
        self.metrics = get_metrics_collector()

        # Configuración por defecto
        self.config = config or ScrapingConfig(
            max_retries=3, timeout=30, concurrent_requests=5
        )

        # Semáforo para concurrencia
        self.semaphore = asyncio.Semaphore(self.config.concurrent_requests)

    @abstractmethod
    async def extract_data(
        self, url: str, rules: List[ExtractorRule]
    ) -> Dict[str, Any]:
        """
        Extraer datos según reglas.

        Args:
            url: URL a procesar
            rules: Reglas de extracción

        Returns:
            Datos extraídos
        """
        pass

    @abstractmethod
    async def validate_data(
        self, data: Dict[str, Any], validator: DataValidator
    ) -> bool:
        """
        Validar datos extraídos.

        Args:
            data: Datos a validar
            validator: Validador a usar

        Returns:
            True si los datos son válidos
        """
        pass


class ScraperEngine:
    """
    Motor de scraping.

    Responsabilidades:
    1. Coordinar scrapers
    2. Gestionar extracciones
    3. Validar resultados
    4. Manejar errores
    """

    def __init__(self):
        """Inicializar motor."""
        self.logger = logging.getLogger(__name__)
        self.metrics = get_metrics_collector()

        # Registro de scrapers
        self.scrapers: Dict[str, Type[BaseScraper]] = {}

        # Cliente HTTP
        self.session: Optional[aiohttp.ClientSession] = None

        # Browser manager
        self.browser_manager = None

    async def __aenter__(self):
        """Inicializar recursos."""
        self.session = aiohttp.ClientSession()
        self.browser_manager = await get_browser_manager()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Liberar recursos."""
        if self.session:
            await self.session.close()

    def register_scraper(self, name: str, scraper_class: Type[BaseScraper]) -> None:
        """
        Registrar nuevo scraper.

        Args:
            name: Nombre del scraper
            scraper_class: Clase del scraper
        """
        self.scrapers[name] = scraper_class

    async def scrape(
        self,
        url: str,
        scraper_name: str,
        rules: List[ExtractorRule],
        validator: Optional[DataValidator] = None,
    ) -> ScrapingResult:
        """
        Realizar scraping.

        Args:
            url: URL a procesar
            scraper_name: Nombre del scraper
            rules: Reglas de extracción
            validator: Validador opcional

        Returns:
            Resultado del scraping
        """
        try:
            start_time = datetime.now()

            # Obtener scraper
            if scraper_name not in self.scrapers:
                raise ValueError(f"Scraper {scraper_name} no encontrado")

            scraper_class = self.scrapers[scraper_name]
            scraper = scraper_class()

            # Extraer datos
            data = await scraper.extract_data(url, rules)

            # Validar si es necesario
            if validator and not await scraper.validate_data(data, validator):
                raise ValueError("Datos inválidos")

            # Registrar métricas
            duration = (datetime.now() - start_time).total_seconds()

            SCRAPING_OPERATIONS.labels(
                scraper_type=scraper_name, status="success"
            ).inc()

            SCRAPING_LATENCY.labels(scraper_type=scraper_name).observe(duration)

            return ScrapingResult(
                success=True,
                data=data,
                metadata={"scraper": scraper_name, "url": url, "duration": duration},
            )

        except Exception as e:
            self.logger.error(f"Error en scraping: {e}")

            SCRAPING_OPERATIONS.labels(scraper_type=scraper_name, status="error").inc()

            return ScrapingResult(success=False, error=str(e))


class HTMLScraper(BaseScraper):
    """Scraper para contenido HTML."""

    async def extract_data(
        self, url: str, rules: List[ExtractorRule]
    ) -> Dict[str, Any]:
        """Extraer datos de HTML."""
        try:
            async with self.semaphore:
                # Obtener browser manager
                browser_manager = await get_browser_manager()

                # Crear sesión
                session = await browser_manager.get_session()

                # Navegar a URL
                result = await browser_manager.execute_action(
                    session.id, "navigate", {"url": url}
                )

                if not result.success:
                    raise Exception(result.error)

                # Extraer datos según reglas
                data = {}
                for rule in rules:
                    result = await browser_manager.execute_action(
                        session.id,
                        "extract",
                        {"selector": rule.selector, "script": rule.extractor},
                    )

                    if result.success:
                        data[rule.name] = result.data

                return data

        except Exception as e:
            self.logger.error(f"Error extrayendo HTML: {e}")
            raise

    async def validate_data(
        self, data: Dict[str, Any], validator: DataValidator
    ) -> bool:
        """Validar datos HTML."""
        try:
            # Aplicar reglas de validación
            for field, rules in validator.rules.items():
                if field not in data:
                    if rules.get("required", False):
                        return False
                    continue

                value = data[field]

                # Validar tipo
                if "type" in rules:
                    if not isinstance(value, rules["type"]):
                        return False

                # Validar patrón
                if "pattern" in rules and isinstance(value, str):
                    if not rules["pattern"].match(value):
                        return False

                # Validar rango
                if "min" in rules and value < rules["min"]:
                    return False

                if "max" in rules and value > rules["max"]:
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error validando HTML: {e}")
            return False


class APIScraper(BaseScraper):
    """Scraper para APIs."""

    async def extract_data(
        self, url: str, rules: List[ExtractorRule]
    ) -> Dict[str, Any]:
        """Extraer datos de API."""
        try:
            async with self.semaphore:
                # Realizar request
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            raise Exception(
                                f"Error {response.status}: {response.reason}"
                            )

                        # Obtener JSON
                        data = await response.json()

                        # Aplicar reglas de extracción
                        result = {}
                        for rule in rules:
                            # Usar JSONPath
                            value = rule.extractor.find(data)
                            if value:
                                result[rule.name] = value[0].value

                        return result

        except Exception as e:
            self.logger.error(f"Error extrayendo API: {e}")
            raise

    async def validate_data(
        self, data: Dict[str, Any], validator: DataValidator
    ) -> bool:
        """Validar datos API."""
        try:
            # Validar esquema JSON
            return validator.schema.validate(data)

        except Exception as e:
            self.logger.error(f"Error validando API: {e}")
            return False


# Instancia global
scraper_engine = ScraperEngine()

# Registrar scrapers
scraper_engine.register_scraper("html", HTMLScraper)
scraper_engine.register_scraper("api", APIScraper)


async def get_scraper_engine() -> ScraperEngine:
    """Obtener instancia del motor."""
    return scraper_engine
