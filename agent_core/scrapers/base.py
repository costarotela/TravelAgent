"""
Base scraper implementation with anti-blocking measures.

Este módulo implementa el framework base para scraping con medidas anti-bloqueo.
Es un componente IMPRESCINDIBLE que proporciona:
1. Manejo de sesiones HTTP
2. Sistema anti-bloqueo
3. Rotación de User Agents
4. Manejo de errores y reintentos

Ejemplo de uso:
    ```python
    config = ScraperConfig(
        base_url="https://ejemplo.com",
        login_required=True,
        credentials=Credentials("user", "pass")
    )

    async with BaseScraper(config) as scraper:
        if await scraper.login():
            data = await scraper.extract_data()
    ```
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
from dataclasses import dataclass

from .session_manager import SessionManager

logger = logging.getLogger(__name__)

@dataclass
class Credentials:
    """Credenciales para login."""
    username: str
    password: str

class ScraperConfig:
    """Configuration for a scraper instance."""
    
    def __init__(
        self,
        base_url: str,
        login_required: bool = False,
        headless: bool = True,
        proxy_enabled: bool = False,
        user_agent_rotation: bool = True,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        max_retries: int = 3,
        credentials: Optional[Credentials] = None
    ):
        self.base_url = base_url
        self.login_required = login_required
        self.headless = headless
        self.proxy_enabled = proxy_enabled
        self.user_agent_rotation = user_agent_rotation
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.credentials = credentials

        # Validar credenciales si se requiere login
        if login_required and not credentials:
            raise ValueError("Se requieren credenciales cuando login_required es True")

class BaseScraper(ABC):
    """Base class for all scrapers."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.session_manager = SessionManager(
            min_delay=config.min_delay,
            max_delay=config.max_delay,
            max_retries=config.max_retries
        )
        self.driver = None
        self.session_active = False
        self._setup_logging()

    def _setup_logging(self):
        """Setup scraper-specific logging."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def initialize(self):
        """Initialize the scraper and browser."""
        try:
            await self._init_driver()
            if self.config.login_required:
                await self.login()
            self.session_active = True
        except Exception as e:
            self.logger.error(f"Failed to initialize scraper: {e}")
            raise

    async def _init_driver(self):
        """Initialize WebDriver with current session configuration."""
        if self.driver:
            await self.close()

        session_config = await self.session_manager.get_session_config()
        
        options = webdriver.ChromeOptions()
        if self.config.headless:
            options.add_argument('--headless')
        
        options.add_argument(f'user-agent={session_config["user_agent"]}')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        for key, value in session_config['headers'].items():
            options.add_argument(f'--header={key}: {value}')

        self.driver = webdriver.Chrome(options=options)
        self.logger.info(f"Initialized WebDriver with User-Agent: {session_config['user_agent']}")

    async def navigate(self, url: str):
        """Navigate to a specific URL."""
        try:
            await self._init_driver()
            self.driver.get(url)
            self.logger.info(f"Navigated to {url}")
            return True
        except Exception as e:
            if await self.session_manager.handle_error(e):
                await self._init_driver()
                return await self.navigate(url)
            self.logger.error(f"Navigation failed to {url}: {e}")
            raise

    async def wait_for_element(
        self, 
        selector: str, 
        timeout: int = None, 
        by: str = By.CSS_SELECTOR
    ) -> bool:
        """Wait for an element to be present on the page."""
        timeout = timeout or 10
        try:
            element = await asyncio.to_thread(
                WebDriverWait(self.driver, timeout).until,
                EC.presence_of_element_located((by, selector))
            )
            return bool(element)
        except TimeoutException:
            self.logger.warning(f"Timeout waiting for element {selector}")
            return False
        except Exception as e:
            self.logger.error(f"Error waiting for element {selector}: {e}")
            raise

    async def extract_text(
        self, 
        selector: str, 
        by: str = By.CSS_SELECTOR
    ) -> Optional[str]:
        """Extract text from an element."""
        try:
            element = await asyncio.to_thread(
                self.driver.find_element, by, selector
            )
            return element.text.strip()
        except Exception as e:
            self.logger.error(f"Failed to extract text from {selector}: {e}")
            return None

    async def cleanup(self):
        """Cleanup resources."""
        if self.driver:
            try:
                await asyncio.to_thread(self.driver.quit)
                self.logger.info("WebDriver cleaned up successfully")
            except Exception as e:
                self.logger.error(f"Error cleaning up WebDriver: {e}")
            finally:
                self.driver = None
                self.session_active = False

    async def close(self):
        """Close WebDriver and reset session."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error closing driver: {e}")
            finally:
                self.driver = None
        
        self.session_manager.reset()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

    @abstractmethod
    async def login(self) -> bool:
        """Login to the provider's website."""
        pass
