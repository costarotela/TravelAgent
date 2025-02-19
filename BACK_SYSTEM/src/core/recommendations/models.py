"""Models for price and supplier analysis."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field


class PriceTrend(str, Enum):
    """Price trend predictions."""

    INCREASING = "increasing"  # Tendencia al alza
    DECREASING = "decreasing"  # Tendencia a la baja
    STABLE = "stable"  # Tendencia estable
    VOLATILE = "volatile"  # Tendencia volátil


class ConfidenceLevel(str, Enum):
    """Confidence levels for analysis."""

    HIGH = "high"  # Alta confianza (>80%)
    MEDIUM = "medium"  # Confianza media (50-80%)
    LOW = "low"  # Baja confianza (<50%)


class PriceAnalysis(BaseModel):
    """Price analysis for a package or service."""

    item_id: str
    current_price: float
    historical_prices: List[Dict[str, Any]]
    trend: PriceTrend
    confidence: ConfidenceLevel
    expected_variation: float  # Variación esperada en porcentaje
    factors: List[str]  # Factores que influyen en el precio
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SupplierMetrics(BaseModel):
    """Metrics for a supplier."""

    reliability_score: float  # 0-1, basado en historial
    price_competitiveness: float  # 0-1, comparado con mercado
    service_quality: float  # 0-1, basado en ratings
    response_time: float  # Tiempo promedio de respuesta en horas
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SupplierAnalysis(BaseModel):
    """Analysis for a supplier."""

    supplier_id: str
    service_type: str
    metrics: SupplierMetrics
    historical_performance: List[Dict[str, Any]]
    confidence: ConfidenceLevel
    recommendations: List[str]  # Recomendaciones de acción
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnalysisContext(BaseModel):
    """Context for analysis."""

    package_data: Dict[str, Any]
    historical_prices: List[Dict[str, Any]]
    market_data: Optional[Dict[str, Any]] = None
    supplier_data: Optional[Dict[str, Any]] = None
    temporal_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
