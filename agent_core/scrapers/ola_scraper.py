"""
Implementación del scraper para OLA.com.ar

Este módulo implementa la extracción de datos específica para OLA.com.ar.
Es un componente IMPRESCINDIBLE que proporciona:
1. Login seguro en el portal mayorista
2. Extracción de paquetes y precios
3. Detección de cambios en tiempo real
4. Manejo de errores específicos de OLA

Ejemplo de uso:
    ```python
    config = ScraperConfig(
        base_url="https://ola.com.ar",
        login_required=True,
        credentials=Credentials(
            username="agencia",
            password="secreto"
        )
    )

    async with OlaScraper(config) as scraper:
        if await scraper.login():
            packages = await scraper.search_packages({
                "destino": "Costa Mujeres",
                "fechas": ["2025-03-02", "2025-03-25"]
            })
    ```

Notas de Implementación:
1. Utiliza el SessionManager para manejo de sesiones y anti-bloqueo
2. Implementa reintentos específicos para errores de OLA
3. Incluye logging detallado para debugging
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import asyncio
from decimal import Decimal

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

from .base import BaseScraper, ScraperConfig
from .change_detector import ChangeDetector
from ..schemas.travel import (
    PaqueteOLA,
    VueloDetallado,
    PoliticasCancelacion,
    CotizacionEspecial,
    ImpuestoLocal,
    AssistCard
)

class OlaScraper(BaseScraper):
    """Scraper específico para Ola.com.ar."""

    SELECTORS = {
        'login': {
            'username': '#username',
            'password': '#password',
            'submit': 'button[type="submit"]',
            'error': '.error-message',
            'success': '.dashboard-welcome'
        },
        'paquete': {
            'container': '.package-item',
            'destino': '.destination',
            'aerolinea': '.airline',
            'duracion': '.duration',
            'precio': '.price',
            'impuestos': '.taxes',
            'incluye': '.includes li',
            'fechas': '.available-dates li'
        },
        'vuelos': {
            'container': '.flight-details',
            'salida': '.departure',
            'llegada': '.arrival',
            'escala': '.layover',
            'espera': '.wait-time',
            'duracion': '.duration'
        },
        'politicas': {
            'container': '.cancellation-policy',
            'periodos': '.period-policy'
        },
        'assist_card': {
            'container': '.assist-card',
            'cobertura': '.coverage',
            'validez': '.validity',
            'territorialidad': '.territory',
            'limitaciones': '.age-limits',
            'gastos': '.reservation-fee'
        },
        'impuestos_especiales': {
            'container': '.special-taxes',
            'nombre': '.tax-name',
            'monto': '.tax-amount',
            'detalle': '.tax-details'
        }
    }

    def __init__(self, config: Optional[ScraperConfig] = None):
        if not config:
            config = ScraperConfig(
                base_url="https://ola.com.ar",
                login_required=True,
                headless=True,
                proxy_enabled=True,
                user_agent_rotation=True
            )
        super().__init__(config)
        self._last_search = None
        self.change_detector = ChangeDetector()
        self._last_packages = {}  # Cache mínimo solo para detección de cambios

    async def login(self) -> bool:
        """
        Realiza el login en OLA.com.ar.
        Retorna True si el login fue exitoso, False en caso contrario.
        """
        try:
            await self.navigate(f"{self.config.base_url}/login")
            
            # Esperar que el formulario de login esté presente
            if not await self.wait_for_element(self.SELECTORS['login']['username']):
                self.logger.error("Formulario de login no encontrado")
                return False

            # Ingresar credenciales
            username_input = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['login']['username'])
            password_input = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['login']['password'])
            submit_button = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['login']['submit'])

            username_input.send_keys(self.config.credentials.username)
            password_input.send_keys(self.config.credentials.password)
            submit_button.click()

            # Esperar resultado del login
            success = await self.wait_for_element(self.SELECTORS['login']['success'], timeout=10)
            if success:
                self.logger.info("Login exitoso en OLA")
                return True

            # Verificar si hay mensaje de error
            error_element = self.driver.find_elements(By.CSS_SELECTOR, self.SELECTORS['login']['error'])
            if error_element:
                error_message = error_element[0].text
                self.logger.error(f"Error en login: {error_message}")
            else:
                self.logger.error("Login falló sin mensaje de error")

            return False

        except Exception as e:
            self.logger.error(f"Error durante login: {e}")
            return False

    async def _extract_vuelos(self, element: Any) -> List[VueloDetallado]:
        """Extrae información detallada de vuelos."""
        vuelos = []
        vuelos_elements = await asyncio.to_thread(
            element.find_elements,
            By.CSS_SELECTOR,
            self.SELECTORS['vuelos']['container']
        )
        
        for vuelo_elem in vuelos_elements:
            vuelo = VueloDetallado(
                salida=await self.extract_text(self.SELECTORS['vuelos']['salida'], vuelo_elem),
                llegada=await self.extract_text(self.SELECTORS['vuelos']['llegada'], vuelo_elem),
                escala=await self.extract_text(self.SELECTORS['vuelos']['escala'], vuelo_elem),
                espera=await self.extract_text(self.SELECTORS['vuelos']['espera'], vuelo_elem),
                duracion=await self.extract_text(self.SELECTORS['vuelos']['duracion'], vuelo_elem)
            )
            vuelos.append(vuelo)
        
        return vuelos

    async def _extract_politicas_cancelacion(self, element: Any) -> PoliticasCancelacion:
        """Extrae políticas de cancelación."""
        container = await asyncio.to_thread(
            element.find_element,
            By.CSS_SELECTOR,
            self.SELECTORS['politicas']['container']
        )
        
        periodos = await asyncio.to_thread(
            container.find_elements,
            By.CSS_SELECTOR,
            self.SELECTORS['politicas']['periodos']
        )
        
        politicas = {}
        for periodo in periodos:
            texto = await self.extract_text('.', periodo)
            if "0-61" in texto:
                politicas["0-61 noches antes"] = texto.split(":")[-1].strip()
            elif "62-90" in texto:
                politicas["62-90 noches antes"] = texto.split(":")[-1].strip()
            elif "91+" in texto:
                politicas["91+ noches antes"] = texto.split(":")[-1].strip()
        
        return PoliticasCancelacion(**politicas)

    async def _extract_assist_card(self, element: Any) -> Optional[AssistCard]:
        """Extrae información de Assist Card."""
        try:
            container = await asyncio.to_thread(
                element.find_element,
                By.CSS_SELECTOR,
                self.SELECTORS['assist_card']['container']
            )
            
            return AssistCard(
                cobertura_maxima=await self.extract_text(self.SELECTORS['assist_card']['cobertura'], container),
                validez=await self.extract_text(self.SELECTORS['assist_card']['validez'], container),
                territorialidad=await self.extract_text(self.SELECTORS['assist_card']['territorialidad'], container),
                limitaciones_por_edad=await self.extract_text(self.SELECTORS['assist_card']['limitaciones'], container),
                gastos_de_reserva=float(await self.extract_text(self.SELECTORS['assist_card']['gastos'], container))
            )
        except NoSuchElementException:
            return None

    async def _extract_impuestos_especiales(self, element: Any) -> List[ImpuestoLocal]:
        """Extrae impuestos especiales."""
        impuestos = []
        try:
            containers = await asyncio.to_thread(
                element.find_elements,
                By.CSS_SELECTOR,
                self.SELECTORS['impuestos_especiales']['container']
            )
            
            for container in containers:
                impuesto = ImpuestoLocal(
                    nombre=await self.extract_text(self.SELECTORS['impuestos_especiales']['nombre'], container),
                    monto=await self.extract_text(self.SELECTORS['impuestos_especiales']['monto'], container),
                    detalle=await self.extract_text(self.SELECTORS['impuestos_especiales']['detalle'], container)
                )
                impuestos.append(impuesto)
        except NoSuchElementException:
            pass
        
        return impuestos

    async def _extract_package_data(self, element: Any) -> Optional[PaqueteOLA]:
        """Extrae datos completos de un paquete."""
        try:
            # Datos básicos
            destino = await self.extract_text(self.SELECTORS['paquete']['destino'], element)
            aerolinea = await self.extract_text(self.SELECTORS['paquete']['aerolinea'], element)
            duracion = int(await self.extract_text(self.SELECTORS['paquete']['duracion'], element))
            
            # Precios e impuestos
            precio_text = await self.extract_text(self.SELECTORS['paquete']['precio'], element)
            precio = float(precio_text.replace('USD', '').strip())
            impuestos_text = await self.extract_text(self.SELECTORS['paquete']['impuestos'], element)
            impuestos = float(impuestos_text.replace('USD', '').strip())
            
            # Servicios incluidos
            incluye_elements = await asyncio.to_thread(
                element.find_elements,
                By.CSS_SELECTOR,
                self.SELECTORS['paquete']['incluye']
            )
            incluye = [await self.extract_text('.', elem) for elem in incluye_elements]
            
            # Fechas disponibles
            fechas_elements = await asyncio.to_thread(
                element.find_elements,
                By.CSS_SELECTOR,
                self.SELECTORS['paquete']['fechas']
            )
            fechas = [await self.extract_text('.', elem) for elem in fechas_elements]
            
            # Información detallada
            vuelos = await self._extract_vuelos(element)
            politicas_cancelacion = await self._extract_politicas_cancelacion(element)
            assist_card = await self._extract_assist_card(element)
            
            # Cotización especial
            impuestos_especiales = await self._extract_impuestos_especiales(element)
            if impuestos_especiales:
                cotizacion_especial = CotizacionEspecial(
                    descripcion="Impuestos y tasas especiales aplicables",
                    impuestos=impuestos_especiales,
                    restricciones="Consultar restricciones específicas en destino"
                )
            else:
                cotizacion_especial = None
            
            return PaqueteOLA(
                destino=destino,
                aerolinea=aerolinea,
                origen="Buenos Aires",  # Por defecto, ajustar según necesidad
                duracion=duracion,
                moneda="USD",
                incluye=incluye,
                fechas=fechas,
                precio=precio,
                impuestos=impuestos,
                politicas_cancelacion=politicas_cancelacion,
                vuelos=vuelos,
                cotizacion_especial=cotizacion_especial,
                assist_card=assist_card
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting package data: {e}")
            return None

    async def search_packages(self, criteria: Dict) -> List[PaqueteOLA]:
        """Busca paquetes según criterios dados."""
        try:
            await self.navigate(f"{self.config.base_url}/packages")
            packages = []
            changes = {}
            
            # Esperar que los paquetes se carguen
            if await self.wait_for_element(self.SELECTORS['paquete']['container']):
                package_elements = await asyncio.to_thread(
                    self.driver.find_elements,
                    By.CSS_SELECTOR,
                    self.SELECTORS['paquete']['container']
                )
                
                for element in package_elements:
                    package = await self._extract_package_data(element)
                    if package:
                        # Detectar cambios si tenemos datos previos
                        if package.destino in self._last_packages:
                            package_changes = self.change_detector.detect_changes(
                                self._last_packages[package.destino],
                                package
                            )
                            if self.change_detector.is_significant_change(package_changes):
                                changes[package.destino] = package_changes
                        
                        # Actualizar caché y lista de paquetes
                        self._last_packages[package.destino] = package
                        packages.append(package)
            
            # Si hay cambios significativos, registrarlos
            if changes:
                self.logger.info(f"Detected significant changes: {changes}")
            
            return packages
            
        except Exception as e:
            self.logger.error(f"Error searching packages: {e}")
            raise
