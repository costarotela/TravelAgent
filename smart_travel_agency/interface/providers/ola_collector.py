"""
Colector específico para el proveedor OLA.
Maneja la estructura específica de paquetes turísticos de OLA.
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
import json

from .collector import ProviderCollector

class OLACollector(ProviderCollector):
    """Implementación específica para OLA."""
    
    def __init__(self, provider_id: str, base_url: str, api_key: str):
        super().__init__(provider_id)
        self.base_url = base_url
        self.api_key = api_key
        self._cached_packages = {}
    
    async def fetch_prices(self) -> Dict[str, Decimal]:
        """
        Obtiene precios de paquetes OLA.
        Retorna un diccionario de id_paquete -> precio_total
        """
        try:
            # Obtener datos del endpoint
            async with self.session.get(
                f"{self.base_url}/paquetes",
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    prices = {}
                    
                    for package in data["paquetes"]:
                        # Generamos un ID único basado en destino + fecha
                        for fecha in package["fechas"]:
                            package_id = f"{package['destino']}_{fecha}"
                            
                            # Precio total incluyendo impuestos
                            total_price = Decimal(str(package["precio"])) + \
                                        Decimal(str(package["impuestos"]))
                            
                            prices[package_id] = total_price
                            
                            # Cachear el paquete completo para uso posterior
                            self._cached_packages[package_id] = {
                                **package,
                                "fecha_seleccionada": fecha
                            }
                    
                    self.last_update = datetime.now()
                    return prices
                else:
                    error = f"Error {response.status}: {await response.text()}"
                    self.errors.append(error)
                    raise ValueError(error)
        except Exception as e:
            self.errors.append(str(e))
            raise
    
    async def check_availability(self, item_ids: List[str]) -> Dict[str, bool]:
        """
        Verifica disponibilidad de paquetes.
        Usa las fechas almacenadas en caché para validar disponibilidad.
        """
        availability = {}
        now = datetime.now()
        
        for item_id in item_ids:
            if package := self._cached_packages.get(item_id):
                try:
                    # Convertir fecha del paquete a datetime
                    fecha_viaje = datetime.strptime(
                        package["fecha_seleccionada"],
                        "%d-%m-%Y"
                    )
                    
                    # Verificar si la fecha es futura y está en la lista
                    is_available = (
                        fecha_viaje > now and
                        package["fecha_seleccionada"] in package["fechas"]
                    )
                    
                    availability[item_id] = is_available
                    
                except (ValueError, KeyError):
                    availability[item_id] = False
            else:
                availability[item_id] = False
        
        return availability
    
    def get_package_details(self, package_id: str) -> Optional[dict]:
        """
        Obtiene detalles completos de un paquete.
        
        Args:
            package_id: ID del paquete (formato: destino_fecha)
        
        Returns:
            Diccionario con detalles del paquete o None si no existe
        """
        return self._cached_packages.get(package_id)
    
    def get_cancellation_policy(self, package_id: str) -> Optional[dict]:
        """
        Obtiene política de cancelación de un paquete.
        
        Args:
            package_id: ID del paquete
        
        Returns:
            Diccionario con políticas de cancelación o None
        """
        if package := self._cached_packages.get(package_id):
            return package.get("politicas_cancelacion")
        return None
    
    def get_flight_details(self, package_id: str) -> Optional[List[dict]]:
        """
        Obtiene detalles de vuelos de un paquete.
        
        Args:
            package_id: ID del paquete
        
        Returns:
            Lista de vuelos o None
        """
        if package := self._cached_packages.get(package_id):
            return package.get("vuelos")
        return None
