"""Scraper for aero.com.ar."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from ...schemas import Flight, Accommodation, Activity
from .base import BaseScraper, AuthenticationError, ScraperError
from .config import AeroScraperConfig, DEFAULT_AERO_CONFIG

logger = logging.getLogger(__name__)


class AeroScraper(BaseScraper):
    """Scraper for aero.com.ar."""

    def __init__(self, username: str, password: str, config: Optional[AeroScraperConfig] = None):
        """Initialize scraper.
        
        Args:
            username: Username for authentication
            password: Password for authentication
            config: Optional scraper configuration
        """
        super().__init__(
            DEFAULT_AERO_CONFIG.base_url,
            username,
            password,
            config or DEFAULT_AERO_CONFIG
        )
        self.config: AeroScraperConfig = config or DEFAULT_AERO_CONFIG
        self.api_base = f"{self.base_url}/{self.config.api_version}"

    async def authenticate(self) -> None:
        """Authenticate with aero.com.ar."""
        try:
            # Get initial session token
            soup = await self._make_request(
                "GET",
                "/iniciar-sesion",
                auth_required=False
            )
            session_token = soup.select_one('input[name="_token"]')["value"]

            # Perform login
            login_data = {
                "_token": session_token,
                "email": self.username,
                "password": self.password
            }

            response = await self._make_request(
                "POST",
                "/iniciar-sesion",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                auth_required=False
            )

            # Check if login successful
            if "Mi Perfil" not in response.text:
                raise AuthenticationError("Login failed")

            # Extract auth token
            cookies = self.session.cookie_jar.filter_cookies(self.base_url)
            self._auth_token = cookies.get("aero_session").value
            self._last_auth = datetime.now()

        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise AuthenticationError(f"Authentication failed: {str(e)}")

    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: datetime,
        return_date: Optional[datetime] = None,
        **kwargs
    ) -> List[Flight]:
        """Search for flights on aero.com.ar.
        
        Args:
            origin: Origin airport code
            destination: Destination airport code
            departure_date: Departure date
            return_date: Optional return date for round trips
            **kwargs: Additional search parameters
            
        Returns:
            List of Flight objects
        """
        try:
            # Build search parameters
            params = {
                "origen": origin,
                "destino": destination,
                "fecha_ida": departure_date.strftime("%d/%m/%Y"),
                "adultos": kwargs.get("adults", 1),
                "menores": kwargs.get("children", 0),
                "infantes": kwargs.get("infants", 0),
                "clase": kwargs.get("cabin", "economica"),
            }
            if return_date:
                params["fecha_vuelta"] = return_date.strftime("%d/%m/%Y")

            # Make search request
            soup = await self._make_request(
                "GET",
                f"/vuelos/buscar?{urlencode(params)}"
            )

            # Extract flight data
            flights = []
            for flight_div in soup.select(".vuelo-card"):
                try:
                    # Extract basic info
                    airline = flight_div.select_one(".aerolinea").text.strip()
                    flight_number = flight_div.select_one(".numero-vuelo").text.strip()
                    price = await self._extract_price(flight_div, ".precio-final")

                    # Extract times
                    departure_str = flight_div.select_one(".hora-salida")["data-timestamp"]
                    arrival_str = flight_div.select_one(".hora-llegada")["data-timestamp"]
                    departure_time = datetime.fromtimestamp(int(departure_str))
                    arrival_time = datetime.fromtimestamp(int(arrival_str))

                    flight = Flight(
                        flight_number=flight_number,
                        airline=airline,
                        origin=origin,
                        destination=destination,
                        departure_time=departure_time,
                        arrival_time=arrival_time,
                        price=Decimal(str(price)),
                        currency="ARS",
                        cabin_class=kwargs.get("cabin", "ECONOMY"),
                        available_seats=int(flight_div.get("data-asientos", 0)),
                        passengers=kwargs.get("adults", 1) + kwargs.get("children", 0)
                    )
                    flights.append(flight)
                except Exception as e:
                    logger.warning(f"Failed to parse flight: {str(e)}")
                    continue

            return flights

        except Exception as e:
            logger.error(f"Flight search failed: {str(e)}")
            raise ScraperError(f"Flight search failed: {str(e)}")

    async def search_accommodations(
        self,
        destination: str,
        check_in: datetime,
        check_out: datetime,
        **kwargs
    ) -> List[Accommodation]:
        """Search for accommodations on aero.com.ar.
        
        Args:
            destination: Destination city
            check_in: Check-in date
            check_out: Check-out date
            **kwargs: Additional search parameters
            
        Returns:
            List of Accommodation objects
        """
        try:
            # Build search parameters
            params = {
                "ciudad": destination,
                "ingreso": check_in.strftime("%d/%m/%Y"),
                "egreso": check_out.strftime("%d/%m/%Y"),
                "habitaciones": kwargs.get("rooms", 1),
                "adultos": kwargs.get("adults", 2),
                "menores": kwargs.get("children", 0),
            }

            # Make search request
            soup = await self._make_request(
                "GET",
                f"/hoteles/buscar?{urlencode(params)}"
            )

            # Extract hotel data
            hotels = []
            for hotel_div in soup.select(".hotel-card"):
                try:
                    name = hotel_div.select_one(".nombre-hotel").text.strip()
                    price = await self._extract_price(hotel_div, ".precio-noche")
                    rating = float(hotel_div.select_one(".calificacion").text.strip() or 0)

                    hotel = Accommodation(
                        hotel_id=hotel_div["data-hotel-id"],
                        name=name,
                        price_per_night=Decimal(str(price)),
                        nights=(check_out - check_in).days,
                        room_type=kwargs.get("room_type", "Standard"),
                        check_in=check_in,
                        check_out=check_out,
                        rating=rating,
                        amenities=self._extract_amenities(hotel_div)
                    )
                    hotels.append(hotel)
                except Exception as e:
                    logger.warning(f"Failed to parse hotel: {str(e)}")
                    continue

            return hotels

        except Exception as e:
            logger.error(f"Hotel search failed: {str(e)}")
            raise ScraperError(f"Hotel search failed: {str(e)}")

    async def search_activities(
        self,
        destination: str,
        date: datetime,
        **kwargs
    ) -> List[Activity]:
        """Search for activities on aero.com.ar.
        
        Args:
            destination: Destination city
            date: Activity date
            **kwargs: Additional search parameters
            
        Returns:
            List of Activity objects
        """
        try:
            # Build search parameters
            params = {
                "ciudad": destination,
                "fecha": date.strftime("%d/%m/%Y"),
                "participantes": kwargs.get("participants", 2),
            }

            # Make search request
            soup = await self._make_request(
                "GET",
                f"/actividades/buscar?{urlencode(params)}"
            )

            # Extract activity data
            activities = []
            for activity_div in soup.select(".actividad-card"):
                try:
                    name = activity_div.select_one(".nombre-actividad").text.strip()
                    price = await self._extract_price(activity_div, ".precio-final")
                    duration_text = activity_div.select_one(".duracion").text.strip()
                    duration = self._parse_duration(duration_text)

                    activity = Activity(
                        activity_id=activity_div["data-actividad-id"],
                        name=name,
                        price=Decimal(str(price)),
                        duration=duration,
                        date=date,
                        participants=kwargs.get("participants", 2),
                        included=True,
                        description=activity_div.select_one(".descripcion").text.strip()
                    )
                    activities.append(activity)
                except Exception as e:
                    logger.warning(f"Failed to parse activity: {str(e)}")
                    continue

            return activities

        except Exception as e:
            logger.error(f"Activity search failed: {str(e)}")
            raise ScraperError(f"Activity search failed: {str(e)}")

    def _extract_amenities(self, hotel_div: BeautifulSoup) -> List[str]:
        """Extract amenities from hotel div."""
        amenities = []
        for amenity in hotel_div.select(".amenidad"):
            name = amenity.get("title", "").strip()
            if name:
                amenities.append(name)
        return amenities

    def _parse_duration(self, duration_text: str) -> timedelta:
        """Parse duration text into timedelta."""
        try:
            # Example: "2 horas 30 minutos" or "45 minutos"
            parts = duration_text.lower().split()
            total_minutes = 0
            
            for i in range(0, len(parts), 2):
                value = int(parts[i])
                unit = parts[i + 1]
                
                if "hora" in unit:
                    total_minutes += value * 60
                elif "minuto" in unit:
                    total_minutes += value
                    
            return timedelta(minutes=total_minutes)
            
        except Exception:
            return timedelta(hours=1)  # Default duration
