"""Implementación de SmartBrowser para scraping inteligente."""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger(__name__)

class SmartBrowser:
    """Navegador inteligente para scraping."""
    
    def __init__(
        self,
        headless: bool = True,
        proxy: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Inicializar navegador.
        
        Args:
            headless: Ejecutar en modo headless
            proxy: Proxy para las conexiones
            user_agent: User agent personalizado
        """
        self.headless = headless
        self.proxy = proxy
        self.user_agent = user_agent
        self.driver = None
        self._setup_driver()

    def _setup_driver(self):
        """Configurar el driver de Selenium."""
        try:
            options = webdriver.ChromeOptions()
            
            if self.headless:
                options.add_argument('--headless')
            
            if self.proxy:
                options.add_argument(f'--proxy-server={self.proxy}')
            
            if self.user_agent:
                options.add_argument(f'user-agent={self.user_agent}')
            
            # Opciones adicionales para mejor rendimiento
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-extensions')
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
            logger.info("Driver de Chrome inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando Chrome driver: {e}")
            raise

    async def navigate(self, url: str):
        """Navegar a una URL.
        
        Args:
            url: URL a visitar
        """
        try:
            await asyncio.to_thread(self.driver.get, url)
            logger.info(f"Navegación exitosa a {url}")
        except Exception as e:
            logger.error(f"Error navegando a {url}: {e}")
            raise

    async def wait_for_element(
        self,
        selector: str,
        timeout: int = 10,
        type: str = 'css'
    ) -> bool:
        """Esperar por un elemento en la página.
        
        Args:
            selector: Selector del elemento
            timeout: Tiempo máximo de espera
            type: Tipo de selector (css/xpath)
            
        Returns:
            bool: True si el elemento fue encontrado
        """
        try:
            by_type = By.CSS_SELECTOR if type == 'css' else By.XPATH
            element = await asyncio.to_thread(
                WebDriverWait(self.driver, timeout).until,
                EC.presence_of_element_located((by_type, selector))
            )
            return bool(element)
        except TimeoutException:
            logger.warning(f"Timeout esperando elemento {selector}")
            return False
        except Exception as e:
            logger.error(f"Error esperando elemento {selector}: {e}")
            return False

    async def execute_script(self, script: str) -> Any:
        """Ejecutar JavaScript en la página.
        
        Args:
            script: Código JavaScript a ejecutar
            
        Returns:
            Any: Resultado de la ejecución
        """
        try:
            result = await asyncio.to_thread(
                self.driver.execute_script,
                script
            )
            return result
        except Exception as e:
            logger.error(f"Error ejecutando script: {e}")
            raise

    def get_page_source(self) -> str:
        """Obtener el código fuente de la página actual.
        
        Returns:
            str: Código fuente HTML
        """
        return self.driver.page_source

    def get_soup(self) -> BeautifulSoup:
        """Obtener objeto BeautifulSoup de la página actual.
        
        Returns:
            BeautifulSoup: Objeto para parsing HTML
        """
        return BeautifulSoup(self.get_page_source(), 'html.parser')

    async def extract_data(self, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Extraer datos usando selectores.
        
        Args:
            selectors: Diccionario de nombres y selectores CSS
            
        Returns:
            Dict[str, Any]: Datos extraídos
        """
        soup = self.get_soup()
        data = {}
        
        for key, selector in selectors.items():
            try:
                element = soup.select_one(selector)
                if element:
                    data[key] = element.text.strip()
            except Exception as e:
                logger.error(f"Error extrayendo {key}: {e}")
                data[key] = None
        
        return data

    async def close(self):
        """Cerrar el navegador."""
        try:
            if self.driver:
                await asyncio.to_thread(self.driver.quit)
                logger.info("Navegador cerrado correctamente")
        except Exception as e:
            logger.error(f"Error cerrando navegador: {e}")
            raise

    async def __aenter__(self):
        """Soporte para context manager async."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup al salir del context manager."""
        await self.close()
