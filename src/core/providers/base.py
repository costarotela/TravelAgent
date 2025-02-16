"""Base provider interface and utilities for travel providers."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SearchCriteria(BaseModel):
    """Base search criteria model."""
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    adults: int = 1
    children: int = 0
    infants: int = 0
    class_type: Optional[str] = None


class TravelPackage(BaseModel):
    """Base travel package model."""
    id: str
    provider: str
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str]
    price: float
    currency: str
    availability: int
    details: Dict[str, Any]
    raw_data: Optional[Dict[str, Any]] = None


class BaseProvider(ABC):
    """Base class for all travel providers."""

    def __init__(self, credentials: Dict[str, str]):
        """Initialize provider with credentials."""
        self.credentials = credentials
        self._validate_credentials()
        self._setup_session()

    @abstractmethod
    def _validate_credentials(self) -> None:
        """Validate provider credentials."""
        pass

    @abstractmethod
    def _setup_session(self) -> None:
        """Setup provider session."""
        pass

    @abstractmethod
    async def search(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """Search for travel packages."""
        pass

    @abstractmethod
    async def get_package_details(self, package_id: str) -> TravelPackage:
        """Get detailed information for a specific package."""
        pass

    @abstractmethod
    async def check_availability(self, package_id: str) -> bool:
        """Check if a package is still available."""
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    @abstractmethod
    async def close(self):
        """Close provider session."""
        pass
