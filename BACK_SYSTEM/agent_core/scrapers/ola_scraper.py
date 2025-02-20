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
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException,
)

from .base import BaseScraper, ScraperConfig
from .change_detector import ChangeDetector
from .validators import DataValidator, ValidationError
from .error_handler import (
    ErrorHandler,
    ScraperError,
    ConnectionError,
    AuthenticationError,
    DataExtractionError,
    BlockedError,
)
from ..schemas.travel import (
    PaqueteOLA,
    VueloDetallado,
    PoliticasCancelacion,
    CotizacionEspecial,
    ImpuestoLocal,
    AssistCard,
)


class OlaScraper(BaseScraper):
    """Scraper específico para Ola.com.ar."""

    SELECTORS = {
        "login": {
            "username": "#username",
            "password": "#password",
            "submit": 'button[type="submit"]',
            "error": ".error-message",
            "success": ".dashboard-welcome",
        },
        "paquete": {
            "container": ".package-item",
            "destino": ".destination",
            "aerolinea": ".airline",
            "duracion": ".duration",
            "precio": ".price",
            "impuestos": ".taxes",
            "incluye": ".includes li",
            "fechas": ".available-dates li",
        },
        "vuelos": {
            "container": ".flight-details",
            "salida": ".departure",
            "llegada": ".arrival",
            "escala": ".layover",
            "espera": ".wait-time",
            "duracion": ".duration",
        },
        "politicas": {
            "container": ".cancellation-policy",
            "periodos": ".period-policy",
        },
        "assist_card": {
            "container": ".assist-card",
            "cobertura": ".coverage",
            "validez": ".validity",
            "territorialidad": ".territory",
            "limitaciones": ".age-limits",
            "gastos": ".reservation-fee",
        },
        "impuestos_especiales": {
            "container": ".special-taxes",
            "nombre": ".tax-name",
            "monto": ".tax-amount",
            "detalle": ".tax-details",
        },
    }

    def __init__(self, config: Optional[ScraperConfig] = None):
        if not config:
            config = ScraperConfig(
                base_url="https://ola.com.ar",
                login_required=True,
                headless=True,
                proxy_enabled=True,
                user_agent_rotation=True,
            )
        super().__init__(config)
        self._last_search = None
        self.change_detector = ChangeDetector()
        self._last_packages = {}
        self.error_handler = ErrorHandler("ola_scraper", self.logger)
        self.validator = DataValidator()

    @property
    def name(self) -> str:
        return "ola_scraper"

    async def _handle_selenium_error(
        self, error: Exception, operation: str
    ) -> ScraperError:
        """Convierte errores de Selenium en errores específicos del scraper."""
        if isinstance(error, TimeoutException):
            return ConnectionError(f"Timeout en {operation}", error)
        elif isinstance(error, NoSuchElementException):
            return DataExtractionError(f"Elemento no encontrado en {operation}", error)
        elif isinstance(error, StaleElementReferenceException):
            return DataExtractionError(f"Elemento obsoleto en {operation}", error)
        elif isinstance(error, WebDriverException):
            if "ERR_PROXY_CONNECTION_FAILED" in str(error):
                return ConnectionError("Error de conexión con proxy", error)
            elif "invalid session id" in str(error):
                return AuthenticationError("Sesión inválida", error)
        return ScraperError(f"Error en {operation}: {str(error)}", error)

    @ErrorHandler.with_retry("login")
    async def login(self) -> bool:
        """Realiza el login en OLA.com.ar con manejo de errores."""
        self.error_handler.log_operation(
            "login", credentials_provided=bool(self.config.credentials)
        )

        try:
            # Navegar a la página de login
            await self.browser.get(f"{self.config.base_url}/login")

            # Ingresar credenciales
            username_input = await self.browser.find_element(
                By.CSS_SELECTOR, self.SELECTORS["login"]["username"]
            )
            password_input = await self.browser.find_element(
                By.CSS_SELECTOR, self.SELECTORS["login"]["password"]
            )

            await username_input.send_keys(self.config.credentials.username)
            await password_input.send_keys(self.config.credentials.password)

            # Click en botón de login
            submit_button = await self.browser.find_element(
                By.CSS_SELECTOR, self.SELECTORS["login"]["submit"]
            )
            await submit_button.click()

            # Verificar login exitoso
            try:
                await self.browser.find_element(
                    By.CSS_SELECTOR, self.SELECTORS["login"]["success"]
                )
                self.error_handler.log_operation("login_success")
                return True
            except NoSuchElementException:
                error_msg = await self.browser.find_element(
                    By.CSS_SELECTOR, self.SELECTORS["login"]["error"]
                )
                raise AuthenticationError(f"Login fallido: {error_msg.text}")

        except Exception as e:
            raise await self._handle_selenium_error(e, "login")

    @ErrorHandler.with_retry("search_packages")
    async def search_packages(self, criteria: Dict) -> List[PaqueteOLA]:
        """Busca paquetes con manejo de errores y reintentos."""
        self.error_handler.log_operation("search_packages", criteria=criteria)

        packages = []
        changes = {}

        try:
            # Aplicar criterios de búsqueda
            await self._apply_search_criteria(criteria)

            # Extraer resultados
            package_elements = await self.browser.find_elements(
                By.CSS_SELECTOR, self.SELECTORS["paquete"]["container"]
            )

            for element in package_elements:
                try:
                    package_data = await self._extract_package_data(element)

                    # Validar datos extraídos
                    self.validator.validate_package(package_data)

                    if package_data:
                        # Detectar cambios
                        if package_data["destino"] in self._last_packages:
                            package_changes = self.change_detector.detect_changes(
                                self._last_packages[package_data["destino"]],
                                package_data,
                            )
                            if self.change_detector.is_significant_change(
                                package_changes
                            ):
                                changes[package_data["destino"]] = package_changes

                        # Actualizar caché y lista
                        self._last_packages[package_data["destino"]] = package_data
                        packages.append(PaqueteOLA(**package_data))

                except (ValidationError, DataExtractionError) as e:
                    self.error_handler.log_operation(
                        "package_extraction_error",
                        error=str(e),
                        package_element=element.get_attribute("outerHTML"),
                    )
                    continue
                except Exception as e:
                    raise await self._handle_selenium_error(e, "extract_package")

            # Registrar cambios detectados
            if changes:
                self.error_handler.log_operation(
                    "package_changes_detected", changes=json.dumps(changes, default=str)
                )

            return packages

        except Exception as e:
            raise await self._handle_selenium_error(e, "search_packages")

    @ErrorHandler.with_retry("extract_package_data")
    async def _extract_package_data(self, element) -> Dict:
        """Extrae datos de un paquete con manejo de errores."""
        try:
            package_data = {
                "destino": await self._get_text(
                    element, self.SELECTORS["paquete"]["destino"]
                ),
                "aerolinea": await self._get_text(
                    element, self.SELECTORS["paquete"]["aerolinea"]
                ),
                "duracion": await self._get_text(
                    element, self.SELECTORS["paquete"]["duracion"]
                ),
                "precio": await self._get_decimal(
                    element, self.SELECTORS["paquete"]["precio"]
                ),
                "impuestos": await self._get_decimal(
                    element, self.SELECTORS["paquete"]["impuestos"]
                ),
                "incluye": await self._get_list(
                    element, self.SELECTORS["paquete"]["incluye"]
                ),
                "fechas": await self._get_list(
                    element, self.SELECTORS["paquete"]["fechas"]
                ),
            }

            # Extraer detalles adicionales
            package_data["vuelos"] = await self._extract_flight_details(element)
            package_data["politicas"] = await self._extract_cancellation_policies(
                element
            )
            package_data["assist_card"] = await self._extract_assist_card(element)
            package_data["impuestos_especiales"] = await self._extract_special_taxes(
                element
            )

            return package_data

        except Exception as e:
            raise await self._handle_selenium_error(e, "extract_package_data")

    async def _get_text(self, element, selector: str) -> str:
        """Obtiene texto de un elemento con manejo de errores."""
        try:
            el = await element.find_element(By.CSS_SELECTOR, selector)
            return await el.text
        except Exception as e:
            raise DataExtractionError(f"Error extrayendo texto de {selector}", e)

    async def _get_decimal(self, element, selector: str) -> Decimal:
        """Obtiene un valor decimal de un elemento con manejo de errores."""
        try:
            text = await self._get_text(element, selector)
            # Limpiar el texto y convertir a Decimal
            cleaned = text.replace("$", "").replace(".", "").replace(",", ".")
            return Decimal(cleaned)
        except Exception as e:
            raise DataExtractionError(f"Error convirtiendo a decimal: {selector}", e)

    async def _get_list(self, element, selector: str) -> List[str]:
        """Obtiene una lista de textos con manejo de errores."""
        try:
            elements = await element.find_elements(By.CSS_SELECTOR, selector)
            return [await el.text for el in elements]
        except Exception as e:
            raise DataExtractionError(f"Error extrayendo lista de {selector}", e)

    @ErrorHandler.with_retry("extract_flight_details")
    async def _extract_flight_details(self, element) -> Dict:
        """Extrae detalles de vuelos con manejo de errores."""
        try:
            flight_container = await element.find_element(
                By.CSS_SELECTOR, self.SELECTORS["vuelos"]["container"]
            )

            flight_data = {
                "salida": await self._get_text(
                    flight_container, self.SELECTORS["vuelos"]["salida"]
                ),
                "llegada": await self._get_text(
                    flight_container, self.SELECTORS["vuelos"]["llegada"]
                ),
                "duracion": await self._get_text(
                    flight_container, self.SELECTORS["vuelos"]["duracion"]
                ),
            }

            # Extraer escalas si existen
            try:
                escalas = await flight_container.find_elements(
                    By.CSS_SELECTOR, self.SELECTORS["vuelos"]["escala"]
                )
                esperas = await flight_container.find_elements(
                    By.CSS_SELECTOR, self.SELECTORS["vuelos"]["espera"]
                )

                flight_data["escalas"] = []
                for escala, espera in zip(escalas, esperas):
                    flight_data["escalas"].append(
                        {
                            "ubicacion": await escala.text,
                            "tiempo_espera": await espera.text,
                        }
                    )
            except NoSuchElementException:
                flight_data["escalas"] = []

            # Validar datos de vuelo
            self.validator.validate_flight(flight_data)
            return flight_data

        except Exception as e:
            raise await self._handle_selenium_error(e, "extract_flight_details")

    @ErrorHandler.with_retry("extract_cancellation_policies")
    async def _extract_cancellation_policies(self, element) -> List[Dict]:
        """Extrae políticas de cancelación con manejo de errores."""
        try:
            policy_container = await element.find_element(
                By.CSS_SELECTOR, self.SELECTORS["politicas"]["container"]
            )

            periods = await policy_container.find_elements(
                By.CSS_SELECTOR, self.SELECTORS["politicas"]["periodos"]
            )

            policies = []
            for period in periods:
                policy_data = await self._get_text(period, "div")
                # Parsear el texto de la política
                parts = policy_data.split("-")
                if len(parts) == 2:
                    policy = {
                        "periodo": parts[0].strip(),
                        "penalidad": parts[1].strip(),
                    }
                    policies.append(policy)

            # Validar políticas
            self.validator.validate_cancellation_policies(policies)
            return policies

        except Exception as e:
            raise await self._handle_selenium_error(e, "extract_cancellation_policies")

    @ErrorHandler.with_retry("extract_assist_card")
    async def _extract_assist_card(self, element) -> Dict:
        """Extrae información de Assist Card con manejo de errores."""
        try:
            assist_container = await element.find_element(
                By.CSS_SELECTOR, self.SELECTORS["assist_card"]["container"]
            )

            assist_data = {
                "cobertura": await self._get_decimal(
                    assist_container, self.SELECTORS["assist_card"]["cobertura"]
                ),
                "validez": await self._get_text(
                    assist_container, self.SELECTORS["assist_card"]["validez"]
                ),
                "territorialidad": await self._get_text(
                    assist_container, self.SELECTORS["assist_card"]["territorialidad"]
                ),
                "limitaciones": await self._get_text(
                    assist_container, self.SELECTORS["assist_card"]["limitaciones"]
                ),
                "gastos_reserva": await self._get_decimal(
                    assist_container, self.SELECTORS["assist_card"]["gastos"]
                ),
            }

            # Validar datos de Assist Card
            self.validator.validate_assist_card(assist_data)
            return assist_data

        except Exception as e:
            raise await self._handle_selenium_error(e, "extract_assist_card")

    @ErrorHandler.with_retry("extract_special_taxes")
    async def _extract_special_taxes(self, element) -> List[Dict]:
        """Extrae impuestos especiales con manejo de errores."""
        try:
            tax_container = await element.find_element(
                By.CSS_SELECTOR, self.SELECTORS["impuestos_especiales"]["container"]
            )

            tax_elements = await tax_container.find_elements(
                By.CSS_SELECTOR, ".tax-item"
            )

            taxes = []
            for tax_element in tax_elements:
                tax_data = {
                    "nombre": await self._get_text(
                        tax_element, self.SELECTORS["impuestos_especiales"]["nombre"]
                    ),
                    "monto": await self._get_decimal(
                        tax_element, self.SELECTORS["impuestos_especiales"]["monto"]
                    ),
                    "detalle": await self._get_text(
                        tax_element, self.SELECTORS["impuestos_especiales"]["detalle"]
                    ),
                }
                taxes.append(tax_data)

            # Validar impuestos especiales
            self.validator.validate_special_taxes(taxes)
            return taxes

        except Exception as e:
            raise await self._handle_selenium_error(e, "extract_special_taxes")

    @ErrorHandler.with_retry("apply_search_criteria")
    async def _apply_search_criteria(self, criteria: Dict) -> None:
        """Aplica criterios de búsqueda con manejo de errores."""
        try:
            # Validar criterios de búsqueda
            self.validator.validate_search_criteria(criteria)

            # Aplicar cada criterio
            for key, value in criteria.items():
                selector = f"input[name='{key}']"
                try:
                    input_element = await self.browser.find_element(
                        By.CSS_SELECTOR, selector
                    )
                    await input_element.clear()
                    await input_element.send_keys(value)
                    await input_element.send_keys(Keys.RETURN)
                except NoSuchElementException:
                    raise DataExtractionError(f"Campo de búsqueda no encontrado: {key}")

            # Esperar a que se actualicen los resultados
            await asyncio.sleep(2)

        except Exception as e:
            raise await self._handle_selenium_error(e, "apply_search_criteria")

    async def _extract_vuelos(self, element: Any) -> List[VueloDetallado]:
        """Extrae información detallada de vuelos."""
        vuelos = []
        vuelos_elements = await asyncio.to_thread(
            element.find_elements,
            By.CSS_SELECTOR,
            self.SELECTORS["vuelos"]["container"],
        )

        for vuelo_elem in vuelos_elements:
            vuelo = VueloDetallado(
                salida=await self.extract_text(
                    self.SELECTORS["vuelos"]["salida"], vuelo_elem
                ),
                llegada=await self.extract_text(
                    self.SELECTORS["vuelos"]["llegada"], vuelo_elem
                ),
                escala=await self.extract_text(
                    self.SELECTORS["vuelos"]["escala"], vuelo_elem
                ),
                espera=await self.extract_text(
                    self.SELECTORS["vuelos"]["espera"], vuelo_elem
                ),
                duracion=await self.extract_text(
                    self.SELECTORS["vuelos"]["duracion"], vuelo_elem
                ),
            )
            vuelos.append(vuelo)

        return vuelos

    async def _extract_politicas_cancelacion(
        self, element: Any
    ) -> PoliticasCancelacion:
        """Extrae políticas de cancelación."""
        container = await asyncio.to_thread(
            element.find_element,
            By.CSS_SELECTOR,
            self.SELECTORS["politicas"]["container"],
        )

        periodos = await asyncio.to_thread(
            container.find_elements,
            By.CSS_SELECTOR,
            self.SELECTORS["politicas"]["periodos"],
        )

        politicas = {}
        for periodo in periodos:
            texto = await self.extract_text(".", periodo)
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
                self.SELECTORS["assist_card"]["container"],
            )

            return AssistCard(
                cobertura_maxima=await self.extract_text(
                    self.SELECTORS["assist_card"]["cobertura"], container
                ),
                validez=await self.extract_text(
                    self.SELECTORS["assist_card"]["validez"], container
                ),
                territorialidad=await self.extract_text(
                    self.SELECTORS["assist_card"]["territorialidad"], container
                ),
                limitaciones_por_edad=await self.extract_text(
                    self.SELECTORS["assist_card"]["limitaciones"], container
                ),
                gastos_de_reserva=float(
                    await self.extract_text(
                        self.SELECTORS["assist_card"]["gastos"], container
                    )
                ),
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
                self.SELECTORS["impuestos_especiales"]["container"],
            )

            for container in containers:
                impuesto = ImpuestoLocal(
                    nombre=await self.extract_text(
                        self.SELECTORS["impuestos_especiales"]["nombre"], container
                    ),
                    monto=await self.extract_text(
                        self.SELECTORS["impuestos_especiales"]["monto"], container
                    ),
                    detalle=await self.extract_text(
                        self.SELECTORS["impuestos_especiales"]["detalle"], container
                    ),
                )
                impuestos.append(impuesto)
        except NoSuchElementException:
            pass

        return impuestos
