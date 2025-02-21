"""Esquemas para el SmartTravelAgent."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


@dataclass
class Flight:
    """Esquema de vuelo."""

    flight_id: UUID
    provider: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    flight_number: str
    airline: str
    price: Decimal
    currency: str
    passengers: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el vuelo a diccionario."""
        return {
            "flight_id": str(self.flight_id),
            "provider": self.provider,
            "origin": self.origin,
            "destination": self.destination,
            "departure_time": self.departure_time.isoformat(),
            "arrival_time": self.arrival_time.isoformat(),
            "flight_number": self.flight_number,
            "airline": self.airline,
            "price": str(self.price),
            "currency": self.currency,
            "passengers": self.passengers,
        }


@dataclass
class Accommodation:
    """Esquema de alojamiento."""

    accommodation_id: UUID
    provider: str
    hotel_id: str
    name: str
    room_type: str
    price_per_night: Decimal
    currency: str
    nights: int
    check_in: datetime
    check_out: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el alojamiento a diccionario."""
        return {
            "accommodation_id": str(self.accommodation_id),
            "provider": self.provider,
            "hotel_id": self.hotel_id,
            "name": self.name,
            "room_type": self.room_type,
            "price_per_night": str(self.price_per_night),
            "currency": self.currency,
            "nights": self.nights,
            "check_in": self.check_in.isoformat(),
            "check_out": self.check_out.isoformat(),
        }


@dataclass
class Activity:
    """Esquema de actividad."""

    activity_id: UUID
    provider: str
    name: str
    description: str
    price: Decimal
    currency: str
    duration: timedelta
    date: datetime
    participants: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la actividad a diccionario."""
        return {
            "activity_id": str(self.activity_id),
            "provider": self.provider,
            "name": self.name,
            "description": self.description,
            "price": str(self.price),
            "currency": self.currency,
            "duration": str(self.duration),
            "date": self.date.isoformat(),
            "participants": self.participants,
        }


@dataclass
class Hotel:
    """Esquema de hotel."""

    id: str
    name: str
    stars: int
    review_score: float
    amenities: List[str]
    popularity_index: float


@dataclass
class Insurance:
    """Esquema de seguro de viaje."""

    coverage_type: str
    price: Decimal
    currency: str
    provider: str
    insurance_id: UUID = field(default_factory=uuid4)
    description: Optional[str] = None
    coverage_details: Optional[Dict[str, Any]] = None
    terms_and_conditions: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el seguro a diccionario."""
        return {
            "insurance_id": str(self.insurance_id),
            "coverage_type": self.coverage_type,
            "price": str(self.price),
            "currency": self.currency,
            "provider": self.provider,
            "description": self.description,
            "coverage_details": self.coverage_details,
            "terms_and_conditions": self.terms_and_conditions,
        }


@dataclass
class TravelPackage:
    """Esquema de paquete de viaje."""

    package_id: UUID
    provider: str
    currency: str
    flights: Optional[List[Flight]] = None
    accommodations: Optional[List[Accommodation]] = None
    activities: Optional[List[Activity]] = None
    insurance: Optional[Insurance] = None
    description: Optional[str] = None
    cancellation_policy: Optional[str] = None
    modification_policy: Optional[str] = None
    payment_options: Optional[List[str]] = None
    margin: Decimal = Decimal("0.15")
    is_refundable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el paquete a diccionario."""
        return {
            "package_id": str(self.package_id),
            "provider": self.provider,
            "currency": self.currency,
            "flights": [f.to_dict() for f in self.flights] if self.flights else None,
            "accommodations": [a.to_dict() for a in self.accommodations] if self.accommodations else None,
            "activities": [a.to_dict() for a in self.activities] if self.activities else None,
            "insurance": self.insurance.to_dict() if self.insurance else None,
            "description": self.description,
            "cancellation_policy": self.cancellation_policy,
            "modification_policy": self.modification_policy,
            "payment_options": self.payment_options,
            "margin": str(self.margin),
            "is_refundable": self.is_refundable,
        }


@dataclass
class CompetitivePosition:
    """Posición competitiva de un paquete."""

    price_percentile: float
    quality_percentile: float
    flexibility_percentile: float
    position: str  # value_leader, premium, budget, standard


@dataclass
class MarketAnalysis:
    """Análisis de mercado."""

    price_analysis: Dict[str, float]
    quality_analysis: Dict[str, Union[float, List[float]]]
    flexibility_analysis: Dict[str, Union[float, List[float]]]
    seasonality_analysis: Dict[str, Union[float, str]]


@dataclass
class ComparisonResult:
    """Resultado de comparación de paquetes."""

    target_id: str
    position: CompetitivePosition
    opportunities: List[Dict[str, str]]
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class PricingStrategy:
    """Estrategia de pricing."""

    type: str  # competitive, value_based, dynamic
    params: Dict[str, Union[float, str]] = field(default_factory=dict)


@dataclass
class DemandForecast:
    """Pronóstico de demanda."""

    destination: str
    start_date: datetime
    end_date: datetime
    daily_demand: List[Tuple[datetime, float]]
    confidence: float
    metadata: Dict[str, Union[int, str]] = field(default_factory=dict)


@dataclass
class PriceFactors:
    """Factores que afectan el precio."""

    base_cost: float
    margin: float
    seasonality: float
    demand: float
    competition: float
    quality: float
    flexibility: float


@dataclass
class OptimizationResult:
    """Resultado de optimización de precios."""

    original_price: float
    optimal_price: float
    margin: float
    roi: float
    strategy: PricingStrategy
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class CustomerProfile:
    """Perfil de cliente."""

    id: str
    preferences: Dict[str, Union[Tuple[float, float], int, List[str]]]
    constraints: Dict[str, Union[float, Tuple[datetime, datetime]]]
    interests: List[str]
    history: List[Dict[str, str]]


@dataclass
class PackageVector:
    """Vector de características de un paquete."""

    price_score: float
    quality_score: float
    location_score: float
    amenities_score: float
    activities_score: float


@dataclass
class RecommendationScore:
    """Score de recomendación."""

    total_score: float
    components: Dict[str, float]


@dataclass
class Recommendation:
    """Recomendación de paquete."""

    package: TravelPackage
    score: RecommendationScore
    reason: str
    metadata: Dict[str, Union[float, str]] = field(default_factory=dict)


class ReconstructionStrategy:
    """Estrategias de reconstrucción de presupuestos."""
    
    PRESERVE_MARGIN = "preserve_margin"
    PRESERVE_PRICE = "preserve_price"
    ADJUST_PROPORTIONAL = "adjust_proportional"
    BEST_ALTERNATIVE = "best_alternative"


@dataclass
class BudgetItem:
    """Item de presupuesto."""
    
    id: str
    type: str
    category: str
    price: Decimal
    cost: Decimal
    rating: float
    availability: float = 1.0
    dates: Dict[str, datetime] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def dict(self) -> Dict[str, Any]:
        """Convierte el item a diccionario."""
        data = {
            "id": self.id,
            "type": self.type,
            "category": self.category,
            "price": float(self.price),
            "cost": float(self.cost),
            "rating": self.rating,
            "availability": self.availability,
            "dates": {k: v.isoformat() for k, v in self.dates.items()},
            "attributes": self.attributes
        }
        return data

    def copy(self):
        """Crea una copia del item."""
        return BudgetItem(
            id=self.id,
            type=self.type,
            category=self.category,
            price=self.price,
            cost=self.cost,
            rating=self.rating,
            availability=self.availability,
            dates=self.dates.copy(),
            attributes=self.attributes.copy()
        )


@dataclass
class Budget:
    """Presupuesto completo."""
    
    id: str
    items: List[BudgetItem]
    criteria: Dict[str, Any]
    dates: Dict[str, datetime]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def dict(self) -> Dict[str, Any]:
        """Convierte el presupuesto a diccionario."""
        data = {
            "id": self.id,
            "items": [item.dict() for item in self.items],
            "criteria": self.criteria,
            "dates": {k: v.isoformat() for k, v in self.dates.items()},
            "metadata": self.metadata
        }
        return data

    def copy(self):
        """Crea una copia del presupuesto."""
        return Budget(
            id=self.id,
            items=[item.copy() for item in self.items],
            criteria=self.criteria.copy(),
            dates=self.dates.copy(),
            metadata=self.metadata.copy()
        )


@dataclass
class SessionState:
    """Estado de una sesión activa."""
    
    session_id: str
    budget_id: str
    start_time: datetime
    last_update: datetime
    stability_score: float = 1.0
    changes_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReconstructionResult:
    """Resultado de una reconstrucción."""
    
    budget_id: str
    strategy: str
    success: bool
    changes_applied: Dict[str, Any]
    stability_impact: float
    execution_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
