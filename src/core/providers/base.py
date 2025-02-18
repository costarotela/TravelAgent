"""Clases base para proveedores de viajes."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import asyncio
import logging
from src.utils.monitoring import monitor

logger = logging.getLogger(__name__)


@dataclass
class SearchCriteria:
    """Criterios de búsqueda."""

    origin: str
    destination: str
    departure_date: datetime
    return_date: Optional[datetime] = None
    adults: int = 1
    children: int = 0
    cabin_class: str = "ECONOMY"

    def is_valid(self) -> bool:
        """Validar criterios de búsqueda."""
        return all(
            [
                self.origin,
                self.destination,
                self.departure_date > datetime.now(),
                self.adults > 0,
                self.adults + self.children <= 9,
            ]
        )


@dataclass
class TravelPackage:
    """Paquete de viaje."""

    id: str
    provider: str
    origin: str
    destination: str
    departure_date: datetime
    return_date: Optional[datetime]
    price: float
    currency: str
    availability: bool
    details: Dict[str, Any]


class RetryConfig:
    """Configuración de reintentos."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        timeout: float = 30.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout = timeout


class TravelProvider(ABC):
    """Clase base para proveedores de viajes."""

    def __init__(self, config: Dict[str, Any]):
        """Inicializar proveedor."""
        self.config = config
        self.name = config.get("name", "unknown")
        self.retry_config = RetryConfig()

    async def __aenter__(self):
        """Iniciar sesión con el proveedor."""
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cerrar sesión con el proveedor."""
        await self.logout()

    @abstractmethod
    async def login(self):
        """Iniciar sesión con el proveedor."""
        pass

    @abstractmethod
    async def logout(self):
        """Cerrar sesión con el proveedor."""
        pass

    @abstractmethod
    async def _search(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """Implementación específica de búsqueda."""
        pass

    async def search(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """
        Buscar paquetes de viaje con reintentos y timeout.

        Args:
            criteria: Criterios de búsqueda

        Returns:
            Lista de paquetes encontrados

        Raises:
            TimeoutError: Si la búsqueda excede el timeout
            Exception: Si hay un error en la búsqueda después de reintentos
        """
        start_time = datetime.now()
        attempt = 0
        last_error = None

        while attempt < self.retry_config.max_retries:
            try:
                # Ejecutar búsqueda con timeout
                results = await asyncio.wait_for(
                    self._search(criteria), timeout=self.retry_config.timeout
                )

                # Registrar métricas de éxito
                duration = (datetime.now() - start_time).total_seconds()
                monitor.log_metric(
                    "search_success",
                    1,
                    {
                        "provider": self.name,
                        "attempt": attempt + 1,
                        "duration": duration,
                    },
                )

                return results

            except asyncio.TimeoutError as e:
                last_error = e
                monitor.log_metric(
                    "search_timeout", 1, {"provider": self.name, "attempt": attempt + 1}
                )

            except Exception as e:
                last_error = e
                monitor.log_metric(
                    "search_error", 1, {"provider": self.name, "attempt": attempt + 1}
                )

            # Calcular delay para reintento
            delay = min(
                self.retry_config.base_delay * (2**attempt), self.retry_config.max_delay
            )

            logger.warning(
                f"Error en búsqueda con {self.name} (intento {attempt + 1}): {last_error}"
                f". Reintentando en {delay}s..."
            )

            await asyncio.sleep(delay)
            attempt += 1

        # Si llegamos aquí, todos los intentos fallaron
        duration = (datetime.now() - start_time).total_seconds()
        monitor.log_metric(
            "search_failed",
            1,
            {"provider": self.name, "duration": duration, "attempts": attempt},
        )

        raise last_error or Exception(f"Búsqueda fallida después de {attempt} intentos")

    def configure_retries(
        self,
        max_retries: Optional[int] = None,
        base_delay: Optional[float] = None,
        max_delay: Optional[float] = None,
        timeout: Optional[float] = None,
    ):
        """Configurar política de reintentos."""
        if max_retries is not None:
            self.retry_config.max_retries = max_retries
        if base_delay is not None:
            self.retry_config.base_delay = base_delay
        if max_delay is not None:
            self.retry_config.max_delay = max_delay
        if timeout is not None:
            self.retry_config.timeout = timeout

    @abstractmethod
    async def get_package_details(self, package_id: str) -> TravelPackage:
        """Obtener detalles de un paquete."""
        pass

    @abstractmethod
    async def check_availability(self, package_id: str) -> bool:
        """Verificar disponibilidad de un paquete."""
        pass


# Alias para compatibilidad
Provider = TravelProvider
