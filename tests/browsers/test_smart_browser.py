"""Tests para el SmartBrowser."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from src.core.browsers.smart_browser import SmartBrowser


@pytest.fixture
def mock_webdriver():
    """Fixture para mockear Selenium webdriver."""
    with patch("selenium.webdriver.Chrome") as mock_chrome:
        driver = MagicMock()
        mock_chrome.return_value = driver
        yield driver


@pytest.fixture
async def browser(mock_webdriver):
    """Fixture para instancia de SmartBrowser."""
    browser = SmartBrowser(headless=True)
    yield browser
    await browser.close()


@pytest.mark.asyncio
class TestSmartBrowser:
    """Suite de pruebas para SmartBrowser."""

    async def test_browser_initialization(self, mock_webdriver):
        """Probar inicialización del navegador."""
        browser = SmartBrowser(
            headless=True, proxy="http://proxy:8080", user_agent="Custom Agent"
        )

        # Verificar opciones de Chrome
        chrome_options = mock_webdriver.options
        assert "--headless" in str(chrome_options.arguments)
        assert "--proxy-server=http://proxy:8080" in str(chrome_options.arguments)
        assert "user-agent=Custom Agent" in str(chrome_options.arguments)

    async def test_navigation(self, browser, mock_webdriver):
        """Probar navegación a URL."""
        url = "https://example.com"
        await browser.navigate(url)

        # Verificar llamada a get
        mock_webdriver.get.assert_called_once_with(url)

    async def test_wait_for_element_success(self, browser, mock_webdriver):
        """Probar espera exitosa por elemento."""
        selector = ".test-class"
        mock_element = MagicMock()
        mock_webdriver.find_element.return_value = mock_element

        result = await browser.wait_for_element(selector, timeout=1)

        assert result is True
        mock_webdriver.find_element.assert_called_with(By.CSS_SELECTOR, selector)

    async def test_wait_for_element_timeout(self, browser, mock_webdriver):
        """Probar timeout en espera de elemento."""
        mock_webdriver.find_element.side_effect = TimeoutException()

        result = await browser.wait_for_element(".not-found", timeout=1)

        assert result is False

    async def test_execute_script(self, browser, mock_webdriver):
        """Probar ejecución de JavaScript."""
        script = "return document.title;"
        mock_webdriver.execute_script.return_value = "Test Title"

        result = await browser.execute_script(script)

        assert result == "Test Title"
        mock_webdriver.execute_script.assert_called_once_with(script)

    def test_get_soup(self, browser, mock_webdriver):
        """Probar obtención de BeautifulSoup."""
        html = "<html><body><div>Test</div></body></html>"
        mock_webdriver.page_source = html

        soup = browser.get_soup()

        assert isinstance(soup, BeautifulSoup)
        assert soup.find("div").text == "Test"

    async def test_extract_data(self, browser, mock_webdriver):
        """Probar extracción de datos."""
        html = """
        <html>
            <body>
                <div class="title">Test Title</div>
                <div class="price">$100</div>
            </body>
        </html>
        """
        mock_webdriver.page_source = html

        selectors = {"title": ".title", "price": ".price"}

        data = await browser.extract_data(selectors)

        assert data["title"] == "Test Title"
        assert data["price"] == "$100"

    async def test_context_manager(self, mock_webdriver):
        """Probar uso como context manager."""
        async with SmartBrowser() as browser:
            assert browser.driver is not None

        # Verificar que se cerró el navegador
        mock_webdriver.quit.assert_called_once()

    async def test_close(self, browser, mock_webdriver):
        """Probar cierre del navegador."""
        await browser.close()
        mock_webdriver.quit.assert_called_once()

    async def test_error_handling(self, browser, mock_webdriver):
        """Probar manejo de errores."""
        # Simular error en navegación
        mock_webdriver.get.side_effect = Exception("Navigation error")

        with pytest.raises(Exception) as exc_info:
            await browser.navigate("https://example.com")

        assert "Navigation error" in str(exc_info.value)
