"""Esquemas para el SmartTravelAgent."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


@dataclass
class Flight:
    """Esquema de vuelo."""

    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    flight_number: str
    airline: str
    price: Decimal
    passengers: int
    flight_id: UUID = field(default_factory=uuid4)


@dataclass
class Accommodation:
    """Esquema de alojamiento."""

    hotel_id: str
    name: str
    room_type: str
    price_per_night: Decimal
    nights: int
    check_in: datetime
    check_out: datetime
    accommodation_id: UUID = field(default_factory=uuid4)

    @property
    def total_price(self) -> Decimal:
        """Calcula el precio total del alojamiento."""
        return self.price_per_night * self.nights


@dataclass
class Activity:
    """Esquema de actividad."""

    activity_id: str
    name: str
    price: Decimal
    duration: timedelta
    participants: int
    date: datetime
    included: bool = True
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def __post_init__(self):
        """Inicializa los campos calculados."""
        if not self.start_time:
            self.start_time = self.date
        if not self.end_time:
            self.end_time = self.date + self.duration


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
class TravelPackage:
    """Esquema de paquete de viaje."""

    destination: str
    start_date: datetime
    end_date: datetime
    price: Decimal
    currency: str
    provider: str
    description: str
    hotel: Optional[Hotel] = None
    flights: Optional[List[Flight]] = None
    accommodation: Optional[Accommodation] = None
    activities: Optional[List[Activity]] = None
    id: UUID = field(default_factory=uuid4)
    cancellation_policy: Optional[str] = None
    modification_policy: Optional[str] = None
    payment_options: Optional[List[str]] = None
    margin: Decimal = Decimal("0.15")
    is_refundable: bool = False

    @property
    def total_price(self) -> Decimal:
        """Calcula el precio total del paquete."""
        from .services import PackageService
        return PackageService.calculate_total_price(self)

    @property
    def check_in_date(self) -> datetime:
        """Obtiene la fecha de check-in."""
        from .services import PackageService
        return PackageService.get_instance().calculate_check_in_date(self)

    @property
    def check_out_date(self) -> datetime:
        """Obtiene la fecha de check-out."""
        from .services import PackageService
        return PackageService.get_instance().calculate_check_out_date(self)

    @property
    def nights(self) -> int:
        """Obtiene el número de noches."""
        from .services import PackageService
        return PackageService.get_instance().calculate_nights(self)

    def is_valid(self) -> bool:
        """Valida el paquete."""
        from .services import PackageService
        return PackageService.get_instance().validate_package(self)


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
