"""Filters for refining travel package search results."""

from abc import ABC, abstractmethod
from datetime import datetime, time
from typing import List, Optional
from dataclasses import dataclass
import logging

from ..providers import TravelPackage
from src.utils.monitoring import monitor

logger = logging.getLogger(__name__)


@dataclass
class PriceRange:
    """Rango de precios."""

    min_price: float
    max_price: float

    def is_valid(self) -> bool:
        """Validar rango de precios."""
        return self.min_price >= 0 and self.max_price >= self.min_price


@dataclass
class TimeRange:
    """Rango de horarios."""

    start_time: time
    end_time: time

    def is_valid(self) -> bool:
        """Validar rango de horarios."""
        return self.start_time <= self.end_time


class BaseFilter(ABC):
    """Base class for all package filters."""

    @abstractmethod
    def apply(self, packages: List[TravelPackage]) -> List[TravelPackage]:
        """Apply filter to list of packages."""
        pass


class PriceFilter(BaseFilter):
    """Filter packages by price range."""

    def __init__(
        self, min_price: Optional[float] = None, max_price: Optional[float] = None
    ):
        """Initialize price filter.

        Args:
            min_price: Minimum price (inclusive)
            max_price: Maximum price (inclusive)
        """
        self.min_price = min_price
        self.max_price = max_price

    def apply(self, packages: List[TravelPackage]) -> List[TravelPackage]:
        """Filter packages by price range."""
        filtered = packages
        if self.min_price is not None:
            filtered = [pkg for pkg in filtered if pkg.price >= self.min_price]
        if self.max_price is not None:
            filtered = [pkg for pkg in filtered if pkg.price <= self.max_price]
        return filtered


class TimeFilter(BaseFilter):
    """Filter packages by departure/arrival time."""

    def __init__(
        self,
        departure_after: Optional[time] = None,
        departure_before: Optional[time] = None,
        return_after: Optional[time] = None,
        return_before: Optional[time] = None,
    ):
        """Initialize time filter.

        Args:
            departure_after: Earliest departure time
            departure_before: Latest departure time
            return_after: Earliest return time
            return_before: Latest return time
        """
        self.departure_after = departure_after
        self.departure_before = departure_before
        self.return_after = return_after
        self.return_before = return_before

    def apply(self, packages: List[TravelPackage]) -> List[TravelPackage]:
        """Filter packages by time constraints."""
        filtered = []
        for pkg in packages:
            # Parse departure time
            dep_datetime = datetime.fromisoformat(pkg.departure_date)
            dep_time = dep_datetime.time()

            # Check departure time constraints
            if self.departure_after and dep_time < self.departure_after:
                continue
            if self.departure_before and dep_time > self.departure_before:
                continue

            # If return time constraints exist, check return flight
            if any([self.return_after, self.return_before]) and pkg.return_date:
                ret_datetime = datetime.fromisoformat(pkg.return_date)
                ret_time = ret_datetime.time()

                if self.return_after and ret_time < self.return_after:
                    continue
                if self.return_before and ret_time > self.return_before:
                    continue

            filtered.append(pkg)

        return filtered


class AirlineFilter(BaseFilter):
    """Filter packages by airline."""

    def __init__(self, airlines: List[str], exclude: bool = False):
        """Initialize airline filter.

        Args:
            airlines: List of airline names or codes
            exclude: If True, exclude these airlines instead of including only them
        """
        self.airlines = set(airline.upper() for airline in airlines)
        self.exclude = exclude

    def apply(self, packages: List[TravelPackage]) -> List[TravelPackage]:
        """Filter packages by airline."""
        return [
            pkg
            for pkg in packages
            if (pkg.details.get("airline", "").upper() in self.airlines) != self.exclude
        ]


class StopsFilter(BaseFilter):
    """Filter packages by number of stops."""

    def __init__(self, max_stops: int):
        """Initialize stops filter.

        Args:
            max_stops: Maximum number of stops allowed
        """
        self.max_stops = max_stops

    def apply(self, packages: List[TravelPackage]) -> List[TravelPackage]:
        """Filter packages by number of stops."""
        return [
            pkg
            for pkg in packages
            if len(pkg.details.get("stops", [])) <= self.max_stops
        ]


class DurationFilter(BaseFilter):
    """Filter packages by flight duration."""

    def __init__(self, max_duration_minutes: int):
        """Initialize duration filter.

        Args:
            max_duration_minutes: Maximum flight duration in minutes
        """
        self.max_duration = max_duration_minutes

    def apply(self, packages: List[TravelPackage]) -> List[TravelPackage]:
        """Filter packages by duration."""
        return [
            pkg
            for pkg in packages
            if self._get_duration_minutes(pkg.details.get("duration", "0"))
            <= self.max_duration
        ]

    def _get_duration_minutes(self, duration: str) -> int:
        """Convert duration string to minutes.

        Handles formats like:
        - "2h 30m"
        - "150m"
        - "2.5h"
        """
        try:
            if "h" in duration and "m" in duration:
                hours, minutes = duration.split("h")
                return int(hours.strip()) * 60 + int(minutes.strip("m").strip())
            elif "h" in duration:
                hours = float(duration.strip("h").strip())
                return int(hours * 60)
            elif "m" in duration:
                return int(duration.strip("m").strip())
            return int(duration)  # Assume minutes if no unit
        except (ValueError, TypeError):
            return 0  # Return 0 for invalid formats


class CompositeFilter(BaseFilter):
    """Combine multiple filters."""

    def __init__(self, filters: List[BaseFilter]):
        """Initialize composite filter.

        Args:
            filters: List of filters to apply
        """
        self.filters = filters

    def apply(self, packages: List[TravelPackage]) -> List[TravelPackage]:
        """Apply all filters in sequence."""
        filtered = packages
        for filter_obj in self.filters:
            filtered = filter_obj.apply(filtered)
        return filtered


class SearchFilters:
    """Filtros de búsqueda."""

    def __init__(
        self,
        price_range: Optional[PriceRange] = None,
        flight_types: Optional[List[str]] = None,
        cabin_classes: Optional[List[str]] = None,
        departure_time: Optional[TimeRange] = None,
        airlines: Optional[List[str]] = None,
        max_stops: Optional[int] = None,
        min_baggage: Optional[int] = None,
    ):
        """Inicializar filtros."""
        self.price_range = price_range
        self.flight_types = flight_types
        self.cabin_classes = cabin_classes
        self.departure_time = departure_time
        self.airlines = airlines
        self.max_stops = max_stops
        self.min_baggage = min_baggage

    def is_valid(self) -> bool:
        """Validar filtros."""
        if self.price_range and not self.price_range.is_valid():
            return False
        if self.departure_time and not self.departure_time.is_valid():
            return False
        if self.max_stops is not None and self.max_stops < 0:
            return False
        if self.min_baggage is not None and self.min_baggage < 0:
            return False
        return True

    def _parse_time(self, time_str: str) -> Optional[time]:
        """Convertir string de tiempo a objeto time."""
        try:
            return datetime.strptime(time_str, "%H:%M").time()
        except (ValueError, TypeError):
            return None

    def _parse_baggage(self, baggage_str: str) -> Optional[int]:
        """Extraer peso de equipaje de string."""
        try:
            # Convertir "23kg" a 23
            return int(baggage_str.lower().replace("kg", ""))
        except (ValueError, AttributeError):
            return None

    def apply(self, packages: List[TravelPackage]) -> List[TravelPackage]:
        """
        Aplicar filtros a lista de paquetes.

        Args:
            packages: Lista de paquetes a filtrar

        Returns:
            Lista filtrada de paquetes
        """
        try:
            filtered = packages[:]
            filters_applied = 0

            # Filtrar por precio
            if self.price_range:
                filtered = [
                    pkg
                    for pkg in filtered
                    if self.price_range.min_price
                    <= pkg.price
                    <= self.price_range.max_price
                ]
                filters_applied += 1

            # Filtrar por tipo de vuelo
            if self.flight_types:
                filtered = [
                    pkg
                    for pkg in filtered
                    if pkg.details.get("type", "").lower()
                    in [t.lower() for t in self.flight_types]
                ]
                filters_applied += 1

            # Filtrar por clase
            if self.cabin_classes:
                filtered = [
                    pkg
                    for pkg in filtered
                    if pkg.details.get("cabin_class", "").lower()
                    in [c.lower() for c in self.cabin_classes]
                ]
                filters_applied += 1

            # Filtrar por horario de salida
            if self.departure_time:
                filtered = [
                    pkg
                    for pkg in filtered
                    if (
                        departure_time := self._parse_time(
                            pkg.details.get("departure_time", "")
                        )
                    )
                    and self.departure_time.start_time
                    <= departure_time
                    <= self.departure_time.end_time
                ]
                filters_applied += 1

            # Filtrar por aerolínea
            if self.airlines:
                filtered = [
                    pkg
                    for pkg in filtered
                    if pkg.details.get("airline", "").lower()
                    in [a.lower() for a in self.airlines]
                ]
                filters_applied += 1

            # Filtrar por número de escalas
            if self.max_stops is not None:
                filtered = [
                    pkg
                    for pkg in filtered
                    if len(pkg.details.get("stops", [])) <= self.max_stops
                ]
                filters_applied += 1

            # Filtrar por equipaje mínimo
            if self.min_baggage is not None:
                filtered = [
                    pkg
                    for pkg in filtered
                    if (
                        baggage := self._parse_baggage(
                            pkg.details.get("baggage", "0kg")
                        )
                    )
                    and baggage >= self.min_baggage
                ]
                filters_applied += 1

            # Registrar métricas
            monitor.log_metric("filters_applied", filters_applied)
            monitor.log_metric(
                "filtered_results", len(filtered), {"total": len(packages)}
            )

            return filtered

        except Exception as e:
            logger.error(f"Error al aplicar filtros: {str(e)}")
            monitor.log_error(e, {"action": "apply_filters"})
            return packages  # En caso de error, devolver lista original

    @classmethod
    def from_dict(cls, data: dict) -> "SearchFilters":
        """Crear filtros desde diccionario."""
        try:
            # Procesar rango de precios
            price_range = None
            if "min_price" in data and "max_price" in data:
                price_range = PriceRange(
                    float(data["min_price"]), float(data["max_price"])
                )

            # Procesar rango de horarios
            departure_time = None
            if "departure_start" in data and "departure_end" in data:
                departure_time = TimeRange(
                    datetime.strptime(data["departure_start"], "%H:%M").time(),
                    datetime.strptime(data["departure_end"], "%H:%M").time(),
                )

            return cls(
                price_range=price_range,
                flight_types=data.get("flight_types"),
                cabin_classes=data.get("cabin_classes"),
                departure_time=departure_time,
                airlines=data.get("airlines"),
                max_stops=data.get("max_stops"),
                min_baggage=data.get("min_baggage"),
            )

        except Exception as e:
            logger.error(f"Error al crear filtros desde dict: {str(e)}")
            monitor.log_error(e, {"action": "create_filters"})
            return cls()  # Devolver filtros vacíos en caso de error
