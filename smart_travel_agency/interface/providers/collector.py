"""
Colectores base para proveedores.
"""
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
from typing import Dict, List, Optional, Any
import aiohttp
from aiohttp.client_exceptions import (
    ClientError,
    ClientConnectorError,
    ServerDisconnectedError,
    ClientResponseError
)

class ProviderError(Exception):
    """Error base para proveedores."""
    def __init__(self, message: str, provider_id: str, original_error: Optional[Exception] = None):
        self.message = message
        self.provider_id = provider_id
        self.original_error = original_error
        super().__init__(f"{provider_id}: {message}")

class AuthenticationError(ProviderError):
    """Error de autenticación."""
    pass

class ConnectionError(ProviderError):
    """Error de conexión."""
    pass

class ProviderCollector:
    """Colector base para todos los proveedores."""
    
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # segundos
    
    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        self.errors: List[str] = []
        self.last_update: Optional[datetime] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_auth: Optional[datetime] = None
        self._auth_valid = False
    
    @property
    def session(self) -> aiohttp.ClientSession:
        """Obtiene la sesión HTTP activa."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def _retry_operation(self, operation: str, func: callable, *args, **kwargs) -> Any:
        """
        Ejecuta una operación con reintentos.
        
        Args:
            operation: Nombre de la operación para logs
            func: Función a ejecutar
            *args: Argumentos posicionales para func
            **kwargs: Argumentos nombrados para func
            
        Returns:
            Resultado de la función
            
        Raises:
            ProviderError: Si todos los reintentos fallan
        """
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                if attempt > 0:
                    await asyncio.sleep(self.RETRY_DELAY * attempt)
                    
                result = await func(*args, **kwargs)
                return result
                
            except AuthenticationError as e:
                # No reintentar errores de autenticación
                self._auth_valid = False
                raise
                
            except (ClientConnectorError, ServerDisconnectedError) as e:
                last_error = ConnectionError(
                    f"Error de conexión en {operation}",
                    self.provider_id,
                    e
                )
                
            except ClientResponseError as e:
                if e.status in (401, 403):
                    raise AuthenticationError(
                        "Credenciales inválidas o expiradas",
                        self.provider_id,
                        e
                    )
                last_error = ProviderError(
                    f"Error del servidor en {operation}: {e.status}",
                    self.provider_id,
                    e
                )
                
            except Exception as e:
                last_error = ProviderError(
                    f"Error inesperado en {operation}: {str(e)}",
                    self.provider_id,
                    e
                )
                
            self.errors.append(str(last_error))
            
        raise last_error or ProviderError(
            f"Todos los reintentos fallaron para {operation}",
            self.provider_id
        )
    
    async def _make_request(self,
                          method: str,
                          url: str,
                          operation: str,
                          **kwargs) -> aiohttp.ClientResponse:
        """
        Realiza una petición HTTP con manejo de errores.
        
        Args:
            method: Método HTTP
            url: URL del endpoint
            operation: Nombre de la operación
            **kwargs: Argumentos adicionales para la petición
            
        Returns:
            Respuesta HTTP
            
        Raises:
            ProviderError: Si la petición falla
        """
        async def _do_request():
            async with self.session.request(method, url, **kwargs) as response:
                if response.status in (401, 403):
                    raise AuthenticationError(
                        "Credenciales inválidas o expiradas",
                        self.provider_id
                    )
                response.raise_for_status()
                return response
                
        return await self._retry_operation(operation, _do_request)
    
    async def check_auth(self) -> bool:
        """
        Verifica si las credenciales son válidas.
        
        Returns:
            True si las credenciales son válidas
        """
        try:
            await self._ensure_session()
            self._auth_valid = True
            return True
        except AuthenticationError:
            self._auth_valid = False
            return False
        except Exception as e:
            self.errors.append(f"Error verificando autenticación: {str(e)}")
            return False
    
    async def _ensure_session(self):
        """Asegura que existe una sesión HTTP activa."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
    
    async def close(self):
        """Cierra la sesión HTTP."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

class APIProviderCollector(ProviderCollector):
    """Colector para proveedores con API REST."""
    
    def __init__(self, provider_id: str, base_url: str, api_key: str):
        super().__init__(provider_id)
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
    
    async def fetch_prices(self) -> Dict[str, Decimal]:
        """Obtiene precios actualizados vía API."""
        try:
            async with self._make_request(
                "GET",
                f"{self.base_url}/prices",
                "fetch_prices"
            ) as response:
                data = await response.json()
                self.last_update = datetime.now()
                return {
                    item_id: Decimal(str(price))
                    for item_id, price in data.items()
                }
        except ProviderError as e:
            self.errors.append(str(e))
            raise
    
    async def check_availability(self, item_ids: List[str]) -> Dict[str, bool]:
        """Verifica disponibilidad vía API."""
        try:
            async with self._make_request(
                "POST",
                f"{self.base_url}/availability",
                "check_availability",
                json={"items": item_ids}
            ) as response:
                return await response.json()
        except ProviderError as e:
            self.errors.append(str(e))
            raise

class WebScraperCollector(ProviderCollector):
    """Colector para proveedores sin API (web scraping)."""
    
    def __init__(self, 
                 provider_id: str, 
                 scraper_config: dict,
                 username: str,
                 password: str):
        super().__init__(provider_id)
        self.config = scraper_config
        self.username = username
        self.password = password
        self._auth_token = None
    
    async def _authenticate(self):
        """Realiza la autenticación con el proveedor."""
        try:
            login_url = self.config["auth"]["login_url"]
            login_data = {
                self.config["auth"]["username_field"]: self.username,
                self.config["auth"]["password_field"]: self.password
            }
            
            async with self._make_request(
                "POST",
                login_url,
                "_authenticate",
                data=login_data
            ) as response:
                if response.status == 200:
                    # Extraer token o cookie de autenticación
                    if "token_selector" in self.config["auth"]:
                        data = await response.json()
                        self._auth_token = self._extract_value(
                            data,
                            self.config["auth"]["token_selector"]
                        )
                        # Agregar token al header de la sesión
                        self.session.headers.update({
                            "Authorization": f"Bearer {self._auth_token}"
                        })
                    else:
                        # Si usa cookies, se manejan automáticamente por la sesión
                        pass
                    
                    self._last_auth = datetime.now()
                else:
                    error = f"Error de autenticación: {response.status}"
                    self.errors.append(error)
                    raise ValueError(error)
                    
        except ProviderError as e:
            self.errors.append(f"Error en autenticación: {str(e)}")
            raise
    
    async def fetch_prices(self) -> Dict[str, Decimal]:
        """Obtiene precios mediante web scraping."""
        try:
            prices = {}
            for item_id, config in self.config["price_selectors"].items():
                async with self._make_request(
                    "GET",
                    config["url"],
                    "fetch_prices"
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        price = self._extract_price(html, config["selector"])
                        prices[item_id] = Decimal(str(price))
                    elif response.status == 401:
                        # Si perdimos autenticación, reintentar una vez
                        await self._authenticate()
                        async with self._make_request(
                            "GET",
                            config["url"],
                            "fetch_prices"
                        ) as retry_response:
                            if retry_response.status == 200:
                                html = await retry_response.text()
                                price = self._extract_price(html, config["selector"])
                                prices[item_id] = Decimal(str(price))
            
            self.last_update = datetime.now()
            return prices
        except ProviderError as e:
            self.errors.append(str(e))
            raise

    async def check_availability(self, item_ids: List[str]) -> Dict[str, bool]:
        """Verifica disponibilidad mediante web scraping."""
        try:
            availability = {}
            for item_id in item_ids:
                if config := self.config["availability_selectors"].get(item_id):
                    async with self._make_request(
                        "GET",
                        config["url"],
                        "check_availability"
                    ) as response:
                        if response.status == 200:
                            html = await response.text()
                            available = self._check_availability_element(
                                html, 
                                config["selector"]
                            )
                            availability[item_id] = available
            return availability
        except ProviderError as e:
            self.errors.append(str(e))
            raise
    
    def _extract_price(self, html: str, selector: str) -> float:
        """Extrae precio usando selector."""
        # Implementación específica de scraping
        pass
    
    def _check_availability_element(self, html: str, selector: str) -> bool:
        """Verifica disponibilidad usando selector."""
        # Implementación específica de scraping
        pass

    def _extract_value(self, data: dict, selector: str) -> str:
        """Extrae valor usando selector."""
        # Implementación específica de extracción de valor
        pass
