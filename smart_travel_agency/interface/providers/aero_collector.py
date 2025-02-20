"""
Colector específico para el proveedor Aéreo.
Maneja la estructura específica de paquetes aéreos y servicios relacionados.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto
from typing import Dict, List, Optional
import aiohttp
from bs4 import BeautifulSoup
from dataclasses import dataclass

from .collector import WebScraperCollector

class EquipajeTipo(Enum):
    """Tipos de equipaje disponibles."""
    MANO = "mano"
    CARRYON = "carryon"
    BODEGA = "bodega"

class ClaseVuelo(Enum):
    """Clases de vuelo disponibles."""
    ECONOMICA = "economica"
    ECONOMICA_PREMIUM = "economica_premium"
    EJECUTIVA = "ejecutiva"
    EJECUTIVA_PREMIUM = "ejecutiva_premium"
    PRIMERA = "primera"
    PRIMERA_PREMIUM = "primera_premium"

class Aerolinea(Enum):
    """Aerolíneas disponibles."""
    TODAS = "todas"
    AMERICAN = "american"
    AEROMEXICO = "aeromexico"
    AEROLINEAS_ARG = "aerolineas_argentinas"
    COPA = "copa"
    LAN = "lan"
    SKY = "sky"
    HAHN = "hahn"

@dataclass
class FiltrosBusqueda:
    """Filtros para búsqueda de vuelos."""
    origen: str
    destino: str
    fecha_ida: str
    fecha_vuelta: Optional[str] = None
    noches: Optional[int] = None
    pasajeros: int = 1
    equipaje: EquipajeTipo = EquipajeTipo.MANO
    clase: ClaseVuelo = ClaseVuelo.ECONOMICA
    max_escalas: Optional[int] = None
    aerolinea: Aerolinea = Aerolinea.TODAS
    precio_min: Optional[float] = None
    precio_max: Optional[float] = None

class AeroCollector(WebScraperCollector):
    """Implementación específica para proveedor aéreo."""
    
    PRECIO_MIN_DEFAULT = 2140
    PRECIO_MAX_DEFAULT = 29040
    
    def __init__(self, provider_id: str, username: str, password: str):
        super().__init__(
            provider_id=provider_id,
            scraper_config={
                "auth": {
                    "login_url": "https://aero.provider/login",
                    "username_field": "user",
                    "password_field": "pass"
                },
                "search_url": "https://aero.provider/search",
                "filters": {
                    "equipaje": "select.luggage-type",
                    "clase": "select.flight-class",
                    "escalas": "select.stops",
                    "aerolinea": "select.airline",
                    "precio": "div.price-range"
                }
            },
            username=username,
            password=password
        )
        self._flight_details = {}

    async def search_flights(self, filtros: FiltrosBusqueda) -> List[dict]:
        """
        Busca vuelos con filtros avanzados.
        
        Args:
            filtros: Objeto FiltrosBusqueda con todos los criterios
            
        Returns:
            Lista de vuelos que cumplen los criterios
        """
        try:
            await self._ensure_session()
            
            # Construir parámetros de búsqueda
            params = {
                "from": filtros.origen,
                "to": filtros.destino,
                "departure": filtros.fecha_ida,
                "passengers": filtros.pasajeros,
                "luggage": filtros.equipaje.value,
                "class": filtros.clase.value,
                "airline": filtros.aerolinea.value,
                "price_min": filtros.precio_min or self.PRECIO_MIN_DEFAULT,
                "price_max": filtros.precio_max or self.PRECIO_MAX_DEFAULT
            }
            
            # Agregar parámetros opcionales
            if filtros.fecha_vuelta:
                params["return"] = filtros.fecha_vuelta
            if filtros.noches:
                params["nights"] = filtros.noches
            if filtros.max_escalas is not None:
                params["max_stops"] = filtros.max_escalas
            
            async with self.session.get(
                self.config["search_url"], 
                params=params
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_search_results(html, filtros)
                else:
                    error = f"Error en búsqueda: {response.status}"
                    self.errors.append(error)
                    return []
                    
        except Exception as e:
            self.errors.append(f"Error en búsqueda de vuelos: {str(e)}")
            return []
    
    def _parse_search_results(self, 
                            html: str, 
                            filtros: FiltrosBusqueda) -> List[dict]:
        """Parsea resultados de búsqueda."""
        soup = BeautifulSoup(html, 'html.parser')
        flights = []
        
        for flight in soup.select("div.flight"):
            try:
                # Extraer datos básicos
                flight_data = {
                    "id": flight["data-id"],
                    "aerolinea": self._extract_text(flight, ".airline"),
                    "precio": self._extract_price(
                        str(flight),
                        ".price span.amount"
                    ),
                    "duracion": self._extract_text(flight, ".duration"),
                    "disponible": "available" in flight.get("class", []),
                    
                    # Datos adicionales
                    "equipaje": self._extract_text(flight, ".luggage-info"),
                    "clase": self._extract_text(flight, ".class-type"),
                    "escalas": self._extract_stops_info(flight),
                    "servicios": self._extract_services(flight)
                }
                
                # Agregar datos de vuelta si es ida y vuelta
                if filtros.fecha_vuelta:
                    flight_data["vuelta"] = {
                        "fecha": self._extract_text(flight, ".return-date"),
                        "duracion": self._extract_text(flight, ".return-duration"),
                        "precio": self._extract_price(
                            str(flight),
                            ".return-price span.amount"
                        )
                    }
                
                flights.append(flight_data)
                
            except Exception as e:
                self.errors.append(f"Error parseando vuelo: {str(e)}")
                continue
        
        return flights
    
    def _extract_stops_info(self, flight_element: BeautifulSoup) -> List[dict]:
        """Extrae información detallada de escalas."""
        stops = []
        for stop in flight_element.select(".stop-info"):
            stops.append({
                "aeropuerto": self._extract_text(stop, ".airport"),
                "tiempo_espera": self._extract_text(stop, ".wait-time"),
                "terminal": self._extract_text(stop, ".terminal"),
                "servicios_escala": self._extract_text(stop, ".stop-services")
            })
        return stops
    
    def _extract_text(self, soup: BeautifulSoup, selector: str) -> str:
        """Extrae texto de un elemento."""
        element = soup.select_one(selector)
        return element.text.strip() if element else ""
    
    def _extract_price(self, html: str, selector: str) -> float:
        """Extrae precio usando BeautifulSoup."""
        soup = BeautifulSoup(html, 'html.parser')
        price_element = soup.select_one(selector)
        if not price_element:
            raise ValueError(f"No se encontró precio con selector {selector}")
            
        # Limpia y convierte el texto a número
        price_text = price_element.text.strip()
        price_text = price_text.replace('$', '').replace(',', '')
        return float(price_text)
    
    def _extract_stops(self, soup: BeautifulSoup) -> List[dict]:
        """Extrae información de escalas."""
        stops = []
        for stop in soup.select("div.stop"):
            stops.append({
                "aeropuerto": self._extract_text(stop, ".airport"),
                "tiempo_espera": self._extract_text(stop, ".wait-time"),
                "terminal": self._extract_text(stop, ".terminal")
            })
        return stops
    
    def _extract_services(self, soup: BeautifulSoup) -> List[dict]:
        """Extrae servicios incluidos en el vuelo."""
        services = []
        for service in soup.select("div.service"):
            services.append({
                "nombre": self._extract_text(service, ".name"),
                "descripcion": self._extract_text(service, ".description"),
                "incluido": "included" in service.get("class", [])
            })
        return services
    
    async def get_flight_details(self, flight_id: str) -> Optional[dict]:
        """
        Obtiene detalles específicos de un vuelo.
        
        Args:
            flight_id: ID del vuelo
            
        Returns:
            Diccionario con detalles o None
        """
        if flight_id in self._flight_details:
            return self._flight_details[flight_id]
            
        try:
            await self._ensure_session()
            url = f"https://aero.provider/flight/{flight_id}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    details = {
                        "origen": self._extract_text(soup, "div.origin"),
                        "destino": self._extract_text(soup, "div.destination"),
                        "fecha_salida": self._extract_text(soup, "div.departure"),
                        "fecha_llegada": self._extract_text(soup, "div.arrival"),
                        "escalas": self._extract_stops(soup),
                        "servicios": self._extract_services(soup)
                    }
                    
                    self._flight_details[flight_id] = details
                    return details
                    
        except Exception as e:
            self.errors.append(f"Error obteniendo detalles de vuelo: {str(e)}")
            return None
