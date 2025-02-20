"""Scraper for ola.com."""

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
from .config import OlaScraperConfig, DEFAULT_OLA_CONFIG

logger = logging.getLogger(__name__)


class OlaScraper(BaseScraper):
    """Scraper for ola.com."""

    def __init__(self, username: str, password: str, config: Optional[OlaScraperConfig] = None):
        """Initialize scraper.
        
        Args:
            username: Username for authentication
            password: Password for authentication
            config: Optional scraper configuration
        """
        super().__init__(
            DEFAULT_OLA_CONFIG.base_url,
            username,
            password,
            config or DEFAULT_OLA_CONFIG
        )
        self.config: OlaScraperConfig = config or DEFAULT_OLA_CONFIG
        self.api_base = f"{self.base_url}/{self.config.api_version}"

    async def authenticate(self) -> None:
        """Authenticate with ola.com."""
        try:
            # First get CSRF token from login page
            soup = await self._make_request(
                "GET",
                "/login",
                auth_required=False
            )
            csrf_token = soup.select_one('input[name="csrf_token"]')["value"]

            # Perform login
            login_data = {
                "csrf_token": csrf_token,
                "username": self.username,
                "password": self.password,
                "remember_me": "true"
            }

            response = await self._make_request(
                "POST",
                "/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                auth_required=False
            )

            # Check if login successful
            if "Mi Cuenta" not in response.text:
                raise AuthenticationError("Login failed")

            # Extract auth token from cookies
            cookies = self.session.cookie_jar.filter_cookies(self.base_url)
            self._auth_token = cookies.get("auth_token").value
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
        """Search for flights on ola.com.
        
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
                "origin": origin,
                "destination": destination,
                "departure": departure_date.strftime("%Y-%m-%d"),
                "adults": kwargs.get("adults", 1),
                "children": kwargs.get("children", 0),
                "infants": kwargs.get("infants", 0),
                "cabin": kwargs.get("cabin", "ECONOMY"),
            }
            if return_date:
                params["return"] = return_date.strftime("%Y-%m-%d")

            # Make search request
            soup = await self._make_request(
                "GET",
                f"/flights/search?{urlencode(params)}"
            )

            # Extract flight data from script tag
            script = soup.find("script", {"id": "flight-data"})
            if not script:
                return []

            flight_data = json.loads(script.string)
            flights = []

            for item in flight_data["flights"]:
                for segment in item["segments"]:
                    flight = Flight(
                        flight_number=segment["flightNumber"],
                        airline=segment["airline"]["name"],
                        origin=segment["origin"]["code"],
                        destination=segment["destination"]["code"],
                        departure_time=datetime.fromisoformat(segment["departure"]),
                        arrival_time=datetime.fromisoformat(segment["arrival"]),
                        price=Decimal(str(item["price"]["amount"])),
                        currency=item["price"]["currency"],
                        cabin_class=segment["cabin"],
                        available_seats=segment.get("availableSeats", 0),
                        passengers=kwargs.get("adults", 1) + kwargs.get("children", 0)
                    )
                    flights.append(flight)

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
        """Search for accommodations on ola.com.
        
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
                "destination": destination,
                "checkin": check_in.strftime("%Y-%m-%d"),
                "checkout": check_out.strftime("%Y-%m-%d"),
                "rooms": kwargs.get("rooms", 1),
                "adults": kwargs.get("adults", 2),
                "children": kwargs.get("children", 0),
            }

            # Make search request
            soup = await self._make_request(
                "GET",
                f"/hotels/search?{urlencode(params)}"
            )

            # Extract hotel data
            hotels = []
            for hotel_div in soup.select(".hotel-card"):
                try:
                    name = hotel_div.select_one(".hotel-name").text.strip()
                    price = await self._extract_price(hotel_div, ".price-amount")
                    rating = float(hotel_div.select_one(".rating-score").text.strip() or 0)
                    
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
        """Search for activities on ola.com.
        
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
                "destination": destination,
                "date": date.strftime("%Y-%m-%d"),
                "participants": kwargs.get("participants", 2),
            }

            # Make search request
            soup = await self._make_request(
                "GET",
                f"/activities/search?{urlencode(params)}"
            )

            # Extract activity data
            activities = []
            for activity_div in soup.select(".activity-card"):
                try:
                    name = activity_div.select_one(".activity-name").text.strip()
                    price = await self._extract_price(activity_div, ".price-amount")
                    duration_text = activity_div.select_one(".duration").text.strip()
                    duration = self._parse_duration(duration_text)
                    
                    activity = Activity(
                        activity_id=activity_div["data-activity-id"],
                        name=name,
                        price=Decimal(str(price)),
                        duration=duration,
                        date=date,
                        participants=kwargs.get("participants", 2),
                        included=True,
                        description=activity_div.select_one(".description").text.strip()
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
        for amenity in hotel_div.select(".amenity-icon"):
            name = amenity.get("title", "").strip()
            if name:
                amenities.append(name)
        return amenities

    def _parse_duration(self, duration_text: str) -> timedelta:
        """Parse duration text into timedelta."""
        try:
            # Example: "2 hours 30 minutes" or "45 minutes"
            parts = duration_text.lower().split()
            total_minutes = 0
            
            for i in range(0, len(parts), 2):
                value = int(parts[i])
                unit = parts[i + 1]
                
                if "hour" in unit:
                    total_minutes += value * 60
                elif "minute" in unit:
                    total_minutes += value
                    
            return timedelta(minutes=total_minutes)
            
        except Exception:
            return timedelta(hours=1)  # Default duration
