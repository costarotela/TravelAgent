"""
Gestor de integraciones API.

Este módulo implementa:
1. Gestión de APIs
2. Control de autenticación
3. Rate limiting
4. Manejo de errores
"""

from typing import Dict, Any, Optional, List, Type
from datetime import datetime
import logging
import asyncio
from abc import ABC, abstractmethod
from prometheus_client import Counter, Histogram
import aiohttp
import jwt
from ratelimit import limits, sleep_and_retry

from ...schemas import (
    APIConfig,
    APICredentials,
    APIResponse,
    RateLimitConfig
)
from ...metrics import get_metrics_collector

# Métricas
API_OPERATIONS = Counter(
    'api_operations_total',
    'Number of API operations',
    ['api_name', 'operation', 'status']
)

API_LATENCY = Histogram(
    'api_operation_latency_seconds',
    'Latency of API operations',
    ['api_name', 'operation']
)

class BaseAPIClient(ABC):
    """
    Cliente API base.
    
    Responsabilidades:
    1. Definir interfaz común
    2. Manejar autenticación
    3. Controlar rate limiting
    """

    def __init__(
        self,
        config: APIConfig,
        credentials: APICredentials
    ):
        """
        Inicializar cliente.
        
        Args:
            config: Configuración de API
            credentials: Credenciales de acceso
        """
        self.logger = logging.getLogger(__name__)
        self.metrics = get_metrics_collector()
        self.config = config
        self.credentials = credentials
        
        # Estado del cliente
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        
        # Control de rate limiting
        self.rate_limiter = RateLimitConfig(
            calls=config.rate_limit.calls,
            period=config.rate_limit.period
        )

    async def __aenter__(self):
        """Inicializar cliente."""
        self.session = aiohttp.ClientSession(
            base_url=self.config.base_url,
            headers=self.config.default_headers
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cerrar cliente."""
        if self.session:
            await self.session.close()

    @abstractmethod
    async def authenticate(self) -> None:
        """Autenticar cliente."""
        pass

    @sleep_and_retry
    @limits(calls=60, period=60)
    async def request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> APIResponse:
        """
        Realizar request a API.
        
        Args:
            method: Método HTTP
            endpoint: Endpoint a llamar
            **kwargs: Argumentos adicionales
            
        Returns:
            Respuesta de la API
        """
        try:
            start_time = datetime.now()
            
            # Verificar autenticación
            if self.needs_auth():
                await self.authenticate()
            
            # Preparar headers
            headers = kwargs.pop("headers", {})
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            # Realizar request
            async with self.session.request(
                method,
                endpoint,
                headers=headers,
                **kwargs
            ) as response:
                # Procesar respuesta
                data = await response.json()
                
                # Registrar métricas
                duration = (datetime.now() - start_time).total_seconds()
                
                API_OPERATIONS.labels(
                    api_name=self.config.name,
                    operation=endpoint,
                    status=response.status
                ).inc()
                
                API_LATENCY.labels(
                    api_name=self.config.name,
                    operation=endpoint
                ).observe(duration)
                
                return APIResponse(
                    success=response.status == 200,
                    status_code=response.status,
                    data=data,
                    headers=dict(response.headers),
                    metadata={
                        "duration": duration,
                        "endpoint": endpoint
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Error en request: {e}")
            
            API_OPERATIONS.labels(
                api_name=self.config.name,
                operation=endpoint,
                status="error"
            ).inc()
            
            return APIResponse(
                success=False,
                error=str(e)
            )

    def needs_auth(self) -> bool:
        """Verificar si necesita autenticación."""
        if not self.auth_token:
            return True
            
        if not self.token_expiry:
            return True
            
        return datetime.now() >= self.token_expiry

class APIManager:
    """
    Gestor de APIs.
    
    Responsabilidades:
    1. Gestionar clientes
    2. Coordinar operaciones
    3. Manejar errores
    """

    def __init__(self):
        """Inicializar gestor."""
        self.logger = logging.getLogger(__name__)
        self.metrics = get_metrics_collector()
        
        # Registro de clientes
        self.clients: Dict[str, Type[BaseAPIClient]] = {}

    def register_client(
        self,
        name: str,
        client_class: Type[BaseAPIClient]
    ) -> None:
        """
        Registrar nuevo cliente.
        
        Args:
            name: Nombre del cliente
            client_class: Clase del cliente
        """
        self.clients[name] = client_class

    async def get_client(
        self,
        name: str,
        config: APIConfig,
        credentials: APICredentials
    ) -> BaseAPIClient:
        """
        Obtener cliente API.
        
        Args:
            name: Nombre del cliente
            config: Configuración
            credentials: Credenciales
            
        Returns:
            Cliente API
        """
        if name not in self.clients:
            raise ValueError(f"Cliente {name} no encontrado")
            
        client_class = self.clients[name]
        return client_class(config, credentials)

class JWTAPIClient(BaseAPIClient):
    """Cliente API con autenticación JWT."""

    async def authenticate(self) -> None:
        """Autenticar con JWT."""
        try:
            # Realizar login
            response = await self.request(
                "POST",
                self.config.auth_endpoint,
                json={
                    "username": self.credentials.username,
                    "password": self.credentials.password
                }
            )
            
            if not response.success:
                raise Exception(
                    f"Error de autenticación: {response.error}"
                )
            
            # Extraer token
            self.auth_token = response.data["token"]
            
            # Decodificar token para expiry
            token_data = jwt.decode(
                self.auth_token,
                options={"verify_signature": False}
            )
            
            self.token_expiry = datetime.fromtimestamp(
                token_data["exp"]
            )
            
        except Exception as e:
            self.logger.error(f"Error en autenticación: {e}")
            raise

class BasicAuthAPIClient(BaseAPIClient):
    """Cliente API con autenticación básica."""

    async def authenticate(self) -> None:
        """Autenticar con credenciales básicas."""
        try:
            # Usar autenticación básica
            auth = aiohttp.BasicAuth(
                self.credentials.username,
                self.credentials.password
            )
            
            # Actualizar sesión
            self.session = aiohttp.ClientSession(
                base_url=self.config.base_url,
                headers=self.config.default_headers,
                auth=auth
            )
            
            # No hay token ni expiración
            self.auth_token = None
            self.token_expiry = None
            
        except Exception as e:
            self.logger.error(f"Error en autenticación: {e}")
            raise

class APIKeyClient(BaseAPIClient):
    """Cliente API con API Key."""

    async def authenticate(self) -> None:
        """Autenticar con API Key."""
        try:
            # Usar API Key como token
            self.auth_token = self.credentials.api_key
            
            # API Key no expira
            self.token_expiry = datetime.max
            
        except Exception as e:
            self.logger.error(f"Error en autenticación: {e}")
            raise

# Instancia global
api_manager = APIManager()

# Registrar clientes
api_manager.register_client("jwt", JWTAPIClient)
api_manager.register_client("basic", BasicAuthAPIClient)
api_manager.register_client("apikey", APIKeyClient)

async def get_api_manager() -> APIManager:
    """Obtener instancia del gestor."""
    return api_manager
