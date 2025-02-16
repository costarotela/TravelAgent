"""Filters for refining travel package search results."""
from abc import ABC, abstractmethod
from datetime import datetime, time
from typing import List, Optional

from ..providers import TravelPackage


class BaseFilter(ABC):
    """Base class for all package filters."""

    @abstractmethod
    def apply(self, packages: List[TravelPackage]) -> List[TravelPackage]:
        """Apply filter to list of packages."""
        pass


class PriceFilter(BaseFilter):
    """Filter packages by price range."""

    def __init__(self, min_price: Optional[float] = None, max_price: Optional[float] = None):
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
        return_before: Optional[time] = None
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
            pkg for pkg in packages
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
            pkg for pkg in packages
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
            pkg for pkg in packages
            if self._get_duration_minutes(pkg.details.get("duration", "0")) <= self.max_duration
        ]

    def _get_duration_minutes(self, duration: str) -> int:
        """Convert duration string to minutes.
        
        Handles formats like:
        - "2h 30m"
        - "150m"
        - "2.5h"
        """
        try:
            if 'h' in duration and 'm' in duration:
                hours, minutes = duration.split('h')
                return int(hours.strip()) * 60 + int(minutes.strip('m').strip())
            elif 'h' in duration:
                hours = float(duration.strip('h').strip())
                return int(hours * 60)
            elif 'm' in duration:
                return int(duration.strip('m').strip())
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
