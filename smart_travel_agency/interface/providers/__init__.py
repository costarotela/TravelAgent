"""
Módulo de integración con proveedores.
"""
from .collector import ProviderCollector, APIProviderCollector, WebScraperCollector
from .ola_collector import OLACollector
from .aero_collector import (
    AeroCollector,
    FiltrosBusqueda,
    EquipajeTipo,
    ClaseVuelo,
    Aerolinea
)
from .service import ProviderService
from .search_service import SearchService

__all__ = [
    'ProviderCollector',
    'APIProviderCollector',
    'WebScraperCollector',
    'OLACollector',
    'AeroCollector',
    'FiltrosBusqueda',
    'EquipajeTipo',
    'ClaseVuelo',
    'Aerolinea',
    'ProviderService',
    'SearchService'
]
