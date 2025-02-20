"""
Schemas for the travel agent core.
"""

from .travel import (
    TravelPackage,
    PoliticasCancelacion,
    PoliticasPago,
    PoliticasReembolso,
    VueloDetallado,
    CustomerProfile,
    SearchCriteria,
    Accommodation,
    Activity,
    Location,
    AccommodationType,
    PackageStatus,
    AnalysisResult,
    SalesQuery,
    PaqueteOLA,
)

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List


@dataclass
class SessionState:
    """Estado de una sesión activa."""

    vendor_id: str
    customer_id: str
    start_time: datetime
    packages: Dict[str, Any]
    modifications: list
    status: str = "active"
    preferences: Optional[Dict[str, Any]] = None


@dataclass
class SalesReport:
    """Reporte de ventas."""

    vendor_id: str
    period: str
    total_sales: float
    total_packages: int
    packages: List[Dict[str, Any]]
    created_at: datetime = datetime.now()


__all__ = [
    "TravelPackage",
    "PoliticasCancelacion",
    "PoliticasPago",
    "PoliticasReembolso",
    "VueloDetallado",
    "CustomerProfile",
    "SearchCriteria",
    "Accommodation",
    "Activity",
    "Location",
    "AccommodationType",
    "PackageStatus",
    "AnalysisResult",
    "SalesQuery",
    "SessionState",
    "SalesReport",
    "PaqueteOLA",
]
