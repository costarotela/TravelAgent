"""
Esquemas de datos del sistema.

Define los modelos de datos principales usando Pydantic.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class Provider(str, Enum):
    """Proveedores soportados."""

    OLA = "OLA"
    AERO = "AERO"
    DESPEGAR = "DESPEGAR"


class AlertType(str, Enum):
    """Tipos de alertas."""

    PRICE_DROP = "price_drop"
    PRICE_RISE = "price_rise"
    OPPORTUNITY = "opportunity"
    AVAILABILITY = "availability"


class PriorityLevel(str, Enum):
    """Niveles de prioridad."""

    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


class SearchCriteria(BaseModel):
    """Criterios de búsqueda."""

    destination: str
    start_date: datetime
    end_date: datetime
    budget: Optional[float] = None
    passengers: int = 1
    room_type: Optional[str] = None
    meal_plan: Optional[str] = None
    required_services: List[str] = Field(default_factory=list)
    excluded_services: List[str] = Field(default_factory=list)


class TravelPackage(BaseModel):
    """Paquete turístico."""

    id: str
    provider: Provider
    title: str
    destination: str
    description: str
    price: float
    currency: str = "USD"
    start_date: datetime
    end_date: datetime
    duration: int
    availability: float
    included_services: List[str]
    excluded_services: List[str]
    room_type: str
    meal_plan: Optional[str] = None
    cancellation_policy: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PriceAlert(BaseModel):
    """Alerta de precio."""

    type: AlertType
    package_id: str
    message: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)


class Recommendation(BaseModel):
    """Recomendación para un paquete."""

    type: str
    priority: PriorityLevel
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PackageAnalysis(BaseModel):
    """Análisis de un paquete."""

    package_id: str
    score: float
    price_analysis: Dict[str, Any]
    criteria_match: float
    services_analysis: Dict[str, Any]
    recommendations: List[Recommendation]
    timestamp: datetime = Field(default_factory=datetime.now)


class Opportunity(BaseModel):
    """Oportunidad detectada."""

    type: str
    package: TravelPackage
    savings: float
    score: float
    valid_until: datetime
    description: str
    conditions: List[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Budget(BaseModel):
    """Presupuesto generado."""

    id: str
    search_criteria: SearchCriteria
    packages: List[TravelPackage]
    total_cost: float
    currency: str = "USD"
    savings: float = 0
    status: str = "draft"
    notes: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
