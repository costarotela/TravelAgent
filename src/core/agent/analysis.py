"""Sistema de análisis del agente."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import numpy as np
from src.core.database.base import db
from src.core.models.travel import TravelPackage, MarketAnalysis
from src.core.cache.redis_cache import cache


@dataclass
class MarketInsight:
    """Insight del mercado."""

    route: Tuple[str, str]  # (origin, destination)
    price_trend: str
    price_volatility: float
    demand_trend: str
    seasonality: str
    recommendation: str
    confidence: float
    supporting_data: Dict


class AnalysisSystem:
    """Sistema de análisis de mercado y generación de insights."""

    def __init__(self):
        self._insights: Dict[str, MarketInsight] = {}
        self._last_analysis: Dict[str, datetime] = {}

    async def analyze_route(
        self, origin: str, destination: str, days: int = 30
    ) -> Optional[MarketInsight]:
        """Analizar una ruta específica."""
        route_key = f"{origin}-{destination}"
        cache_key = f"market_insight:{route_key}"

        # Intentar obtener del caché
        cached_insight = await cache.get(cache_key)
        if cached_insight:
            return MarketInsight(**cached_insight)

        # Obtener datos históricos
        with db.get_session() as session:
            # Obtener paquetes recientes
            packages = (
                session.query(TravelPackage)
                .filter(
                    TravelPackage.origin == origin,
                    TravelPackage.destination == destination,
                    TravelPackage.created_at
                    >= datetime.utcnow() - timedelta(days=days),
                )
                .order_by(TravelPackage.created_at.asc())
                .all()
            )

            if not packages:
                return None

            # Obtener análisis de mercado
            analyses = (
                session.query(MarketAnalysis)
                .filter(
                    MarketAnalysis.origin == origin,
                    MarketAnalysis.destination == destination,
                    MarketAnalysis.analysis_date
                    >= datetime.utcnow() - timedelta(days=days),
                )
                .order_by(MarketAnalysis.analysis_date.asc())
                .all()
            )

            # Análisis detallado
            prices = [p.price for p in packages]
            dates = [p.created_at for p in packages]
            availability = [p.availability for p in packages]

            # 1. Análisis de precios
            price_trend = self._analyze_price_trend(prices)
            volatility = self._calculate_volatility(prices)

            # 2. Análisis de demanda
            demand_trend = self._analyze_demand_trend(availability)

            # 3. Análisis de estacionalidad
            seasonality = self._analyze_seasonality(dates, prices)

            # 4. Generar recomendación
            recommendation = self._generate_recommendation(
                price_trend, volatility, demand_trend, seasonality
            )

            # 5. Calcular confianza
            confidence = self._calculate_confidence(len(packages), volatility)

            # Crear insight
            insight = MarketInsight(
                route=(origin, destination),
                price_trend=price_trend,
                price_volatility=volatility,
                demand_trend=demand_trend,
                seasonality=seasonality,
                recommendation=recommendation,
                confidence=confidence,
                supporting_data={
                    "sample_size": len(packages),
                    "avg_price": sum(prices) / len(prices),
                    "min_price": min(prices),
                    "max_price": max(prices),
                    "price_range": max(prices) - min(prices),
                    "avg_availability": sum(availability) / len(availability),
                },
            )

            # Guardar en caché
            try:
                await cache.set(
                    cache_key,
                    {
                        "route": insight.route,
                        "price_trend": insight.price_trend,
                        "price_volatility": insight.price_volatility,
                        "demand_trend": insight.demand_trend,
                        "seasonality": insight.seasonality,
                        "recommendation": insight.recommendation,
                        "confidence": insight.confidence,
                        "supporting_data": insight.supporting_data,
                    },
                    ttl=3600,  # 1 hora
                )
            except Exception:
                # Log error pero no fallar
                pass

            return insight

    def _analyze_price_trend(self, prices: List[float]) -> str:
        """Analizar tendencia de precios."""
        if len(prices) < 2:
            return "insufficient_data"

        # Calcular cambio porcentual
        first_half = prices[: len(prices) // 2]
        second_half = prices[len(prices) // 2 :]

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        change = ((second_avg - first_avg) / first_avg) * 100

        if change > 10:
            return "strongly_bullish"
        elif change > 5:
            return "bullish"
        elif change < -10:
            return "strongly_bearish"
        elif change < -5:
            return "bearish"
        return "neutral"

    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calcular volatilidad de precios."""
        if len(prices) < 2:
            return 0.0

        # Usar desviación estándar normalizada
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        std_dev = variance**0.5

        return (std_dev / mean) * 100  # Coeficiente de variación

    def _analyze_demand_trend(self, availability: List[int]) -> str:
        """Analizar tendencia de demanda."""
        if len(availability) < 2:
            return "insufficient_data"

        # Comparar disponibilidad promedio
        first_half = availability[: len(availability) // 2]
        second_half = availability[len(availability) // 2 :]

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        # Menor disponibilidad = mayor demanda
        change = ((first_avg - second_avg) / first_avg) * 100

        if change > 20:
            return "very_high"
        elif change > 10:
            return "high"
        elif change < -20:
            return "very_low"
        elif change < -10:
            return "low"
        return "stable"

    def _analyze_seasonality(self, dates: List[datetime], prices: List[float]) -> str:
        """Analizar estacionalidad."""
        if len(dates) < 7:  # Necesitamos al menos una semana
            return "insufficient_data"

        # Analizar patrones por día de la semana
        daily_prices = defaultdict(list)
        for date, price in zip(dates, prices):
            daily_prices[date.weekday()].append(price)

        # Calcular variación por día
        daily_avgs = {
            day: sum(prices) / len(prices) for day, prices in daily_prices.items()
        }

        # Calcular variación
        avg_price = sum(prices) / len(prices)
        max_variation = max(
            abs(price - avg_price) / avg_price * 100 for price in daily_avgs.values()
        )

        if max_variation > 15:
            return "highly_seasonal"
        elif max_variation > 8:
            return "moderately_seasonal"
        return "non_seasonal"

    def _generate_recommendation(
        self, price_trend: str, volatility: float, demand_trend: str, seasonality: str
    ) -> str:
        """Generar recomendación basada en análisis."""
        if price_trend in ["strongly_bearish", "bearish"] and demand_trend in [
            "high",
            "very_high",
        ]:
            return "strong_buy"
        elif price_trend in ["strongly_bullish", "bullish"] and demand_trend in [
            "low",
            "very_low",
        ]:
            return "strong_sell"
        elif volatility > 20:
            return "high_risk"
        elif price_trend == "neutral" and demand_trend == "stable":
            return "hold"
        elif seasonality == "highly_seasonal":
            return "seasonal_opportunity"
        return "monitor"

    def _calculate_confidence(self, sample_size: int, volatility: float) -> float:
        """Calcular nivel de confianza."""
        # Base: tamaño de muestra
        base_confidence = min(0.7, sample_size / 100)

        # Ajuste por volatilidad
        volatility_factor = max(0, 1 - (volatility / 100))

        return base_confidence * volatility_factor


# Instancia global
analysis_system = AnalysisSystem()
