"""Esquemas para el SmartTravelAgent."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

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
    id: str
    hotel: Hotel
    destination: str
    check_in: datetime
    nights: int
    total_price: float
    cancellation_policy: str
    modification_policy: str
    payment_options: List[str]

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
    parameters: Dict[str, Union[float, str]] = field(default_factory=dict)

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

@dataclass
class OptimizationResult:
    """Resultado de optimización de precios."""
    original_price: float
    optimized_price: float
    margin: float
    roi: float
    factors: Dict[str, float]
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
