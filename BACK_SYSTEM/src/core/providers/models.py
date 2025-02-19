"""Common models for providers."""

from typing import Dict, Optional
from pydantic import BaseModel


class SearchCriteria(BaseModel):
    """Search criteria for travel packages."""

    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    adults: int = 1
    children: int = 0
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    class_type: Optional[str] = None
    flexible_dates: bool = False


class TravelPackage(BaseModel):
    """Travel package information."""

    id: str
    provider: str
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    price: float
    currency: str = "USD"
    class_type: str
    seats_available: int
    description: Optional[str] = None
    raw_data: Optional[Dict] = None
