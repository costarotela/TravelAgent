"""Clases base para proveedores de viajes."""
from dataclasses import dataclass
from datetime import date
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

@dataclass
class SearchCriteria:
    """Criterios de búsqueda."""
    origin: str
    destination: str
    departure_date: date
    return_date: Optional[date] = None
    adults: int = 1
    children: int = 0
    infants: int = 0
    class_type: Optional[str] = None

@dataclass
class TravelPackage:
    """Paquete de viaje (vuelo, hotel, etc.)."""
    id: str
    provider: str
    type: str  # 'flight', 'hotel', 'transfer', etc.
    origin: str
    destination: str
    departure_date: date
    return_date: Optional[date]
    price: float
    currency: str
    details: Dict[str, Any]

class TravelProvider(ABC):
    """Clase base para proveedores de viajes."""

    def __init__(self, config: Dict[str, Any]):
        """Inicializar proveedor."""
        self.config = config
        self.name = config.get("name", "unknown")

    @abstractmethod
    async def search_packages(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """Buscar paquetes de viaje."""
        pass

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
