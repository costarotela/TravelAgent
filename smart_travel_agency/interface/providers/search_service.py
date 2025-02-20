"""
Servicio unificado de búsqueda de vuelos.
"""
from datetime import datetime
from typing import Dict, List, Optional
import asyncio

from .service import ProviderService
from .aero_collector import (
    AeroCollector,
    FiltrosBusqueda,
    EquipajeTipo,
    ClaseVuelo,
    Aerolinea
)

class SearchService:
    """Servicio que unifica búsquedas entre proveedores."""
    
    def __init__(self, provider_service: ProviderService):
        """
        Inicializa el servicio de búsqueda.
        
        Args:
            provider_service: Servicio de proveedores configurado
        """
        self._provider_service = provider_service
        
    async def search_flights(self,
                           origen: str,
                           destino: str,
                           fecha_ida: str,
                           fecha_vuelta: Optional[str] = None,
                           noches: Optional[int] = None,
                           pasajeros: int = 1,
                           equipaje: Optional[EquipajeTipo] = None,
                           clase: Optional[ClaseVuelo] = None,
                           max_escalas: Optional[int] = None,
                           aerolinea: Optional[Aerolinea] = None,
                           precio_min: Optional[float] = None,
                           precio_max: Optional[float] = None) -> Dict[str, List[dict]]:
        """
        Busca vuelos en todos los proveedores configurados.
        
        Args:
            origen: Código de aeropuerto origen
            destino: Código de aeropuerto destino
            fecha_ida: Fecha de ida (YYYY-MM-DD)
            fecha_vuelta: Fecha de vuelta opcional
            noches: Número de noches
            pasajeros: Número de pasajeros
            equipaje: Tipo de equipaje
            clase: Clase de vuelo
            max_escalas: Máximo número de escalas
            aerolinea: Aerolínea específica
            precio_min: Precio mínimo
            precio_max: Precio máximo
            
        Returns:
            Diccionario con resultados por proveedor
        """
        results = {}
        search_tasks = []
        
        # Preparar filtros para búsqueda en Aero
        aero_filtros = FiltrosBusqueda(
            origen=origen,
            destino=destino,
            fecha_ida=fecha_ida,
            fecha_vuelta=fecha_vuelta,
            noches=noches,
            pasajeros=pasajeros,
            equipaje=equipaje or EquipajeTipo.MANO,
            clase=clase or ClaseVuelo.ECONOMICA,
            max_escalas=max_escalas,
            aerolinea=aerolinea or Aerolinea.TODAS,
            precio_min=precio_min,
            precio_max=precio_max
        )
        
        # Buscar en cada proveedor configurado
        for provider_id, collector in self._provider_service._collectors.items():
            if isinstance(collector, AeroCollector):
                # Usar filtros avanzados para Aero
                task = self._search_aero(collector, aero_filtros)
            else:
                # Búsqueda básica para otros proveedores
                task = self._search_basic(
                    collector,
                    origen,
                    destino,
                    fecha_ida,
                    fecha_vuelta,
                    pasajeros
                )
            search_tasks.append((provider_id, task))
        
        # Ejecutar búsquedas en paralelo
        for provider_id, task in search_tasks:
            try:
                results[provider_id] = await task
            except Exception as e:
                results[provider_id] = {
                    "error": str(e),
                    "vuelos": []
                }
        
        return results
    
    async def _search_aero(self,
                          collector: AeroCollector,
                          filtros: FiltrosBusqueda) -> dict:
        """Búsqueda específica para proveedor Aero."""
        try:
            vuelos = await collector.search_flights(filtros)
            return {
                "error": None,
                "vuelos": vuelos
            }
        except Exception as e:
            return {
                "error": str(e),
                "vuelos": []
            }
    
    async def _search_basic(self,
                          collector: 'ProviderCollector',
                          origen: str,
                          destino: str,
                          fecha_ida: str,
                          fecha_vuelta: Optional[str],
                          pasajeros: int) -> dict:
        """Búsqueda básica para otros proveedores."""
        try:
            # Adaptar según la interfaz específica del proveedor
            if hasattr(collector, 'search_flights'):
                vuelos = await collector.search_flights(
                    origin=origen,
                    destination=destino,
                    date=fecha_ida
                )
                return {
                    "error": None,
                    "vuelos": vuelos
                }
            else:
                return {
                    "error": "Proveedor no soporta búsqueda de vuelos",
                    "vuelos": []
                }
        except Exception as e:
            return {
                "error": str(e),
                "vuelos": []
            }
