"""Módulo para estimación avanzada de impacto de acciones."""
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta

@dataclass
class MarketCondition:
    """Condición del mercado para una ruta específica."""
    volatility: float
    trend: str
    demand: float
    seasonality: float
    competition_level: float

@dataclass
class HistoricalImpact:
    """Impacto histórico de acciones similares."""
    avg_impact: float
    success_rate: float
    confidence_level: float
    sample_size: int
    recency_factor: float

class ImpactEstimator:
    """Sistema avanzado de estimación de impacto."""
    
    def __init__(self):
        self.weight_historical = 0.4
        self.weight_market = 0.4
        self.weight_volatility = 0.2
        self._cache = {}
        
    async def estimate_impact(
        self,
        action_type: str,
        origin: str,
        destination: str,
        market_data: Dict,
        historical_data: Optional[List] = None
    ) -> Dict:
        """Estima el impacto esperado de una acción."""
        # Analizar condiciones de mercado
        market_condition = self._analyze_market_conditions(
            origin,
            destination,
            market_data
        )
        
        # Obtener impacto histórico
        historical_impact = await self._get_historical_impact(
            action_type,
            origin,
            destination,
            historical_data
        )
        
        # Calcular impacto estimado
        estimated_impact = self._calculate_weighted_impact(
            market_condition,
            historical_impact
        )
        
        # Calcular confianza
        confidence = self._calculate_confidence(
            market_condition,
            historical_impact
        )
        
        return {
            'estimated_impact': estimated_impact,
            'confidence': confidence,
            'market_condition': market_condition,
            'historical_impact': historical_impact
        }
    
    def _analyze_market_conditions(
        self,
        origin: str,
        destination: str,
        market_data: Dict
    ) -> MarketCondition:
        """Analiza las condiciones actuales del mercado."""
        # Calcular volatilidad
        prices = market_data.get('prices', [])
        volatility = np.std(prices) / np.mean(prices) if prices else 0.0
        
        # Analizar tendencia
        trend = self._analyze_trend(prices)
        
        # Calcular demanda
        demand = market_data.get('demand_score', 0.5)
        
        # Calcular estacionalidad
        seasonality = self._calculate_seasonality(
            origin,
            destination,
            market_data
        )
        
        # Analizar competencia
        competition = self._analyze_competition(market_data)
        
        return MarketCondition(
            volatility=volatility,
            trend=trend,
            demand=demand,
            seasonality=seasonality,
            competition_level=competition
        )
    
    async def _get_historical_impact(
        self,
        action_type: str,
        origin: str,
        destination: str,
        historical_data: Optional[List]
    ) -> HistoricalImpact:
        """Obtiene y analiza el impacto histórico de acciones similares."""
        if historical_data is None:
            historical_data = []
            
        # Filtrar acciones similares
        similar_actions = [
            action for action in historical_data
            if action['type'] == action_type and
            action['origin'] == origin and
            action['destination'] == destination
        ]
        
        if not similar_actions:
            return HistoricalImpact(
                avg_impact=0.0,
                success_rate=0.0,
                confidence_level=0.0,
                sample_size=0,
                recency_factor=0.0
            )
        
        # Calcular métricas
        impacts = [action['impact'] for action in similar_actions]
        successes = [action['success'] for action in similar_actions]
        dates = [action['date'] for action in similar_actions]
        
        avg_impact = np.mean(impacts)
        success_rate = sum(successes) / len(successes)
        sample_size = len(similar_actions)
        
        # Calcular factor de recencia
        recency_factor = self._calculate_recency_factor(dates)
        
        # Calcular nivel de confianza
        confidence_level = self._calculate_confidence_level(
            sample_size,
            success_rate,
            recency_factor
        )
        
        return HistoricalImpact(
            avg_impact=avg_impact,
            success_rate=success_rate,
            confidence_level=confidence_level,
            sample_size=sample_size,
            recency_factor=recency_factor
        )
    
    def _calculate_weighted_impact(
        self,
        market_condition: MarketCondition,
        historical_impact: HistoricalImpact
    ) -> float:
        """Calcula el impacto estimado usando pesos dinámicos."""
        # Ajustar pesos basado en la calidad de los datos
        weights = self._adjust_weights(market_condition, historical_impact)
        
        # Calcular componentes
        market_impact = self._calculate_market_impact(market_condition)
        historical_component = historical_impact.avg_impact * historical_impact.recency_factor
        volatility_adjustment = self._calculate_volatility_adjustment(market_condition.volatility)
        
        # Calcular impacto final
        estimated_impact = (
            weights['historical'] * historical_component +
            weights['market'] * market_impact +
            weights['volatility'] * volatility_adjustment
        )
        
        return max(0.0, min(1.0, estimated_impact))
    
    def _calculate_confidence(
        self,
        market_condition: MarketCondition,
        historical_impact: HistoricalImpact
    ) -> float:
        """Calcula el nivel de confianza en la estimación."""
        # Factores de confianza
        market_confidence = 1.0 - market_condition.volatility
        historical_confidence = historical_impact.confidence_level
        sample_confidence = min(1.0, historical_impact.sample_size / 10.0)
        
        # Pesos de confianza
        weights = self._adjust_weights(market_condition, historical_impact)
        
        # Calcular confianza final
        confidence = (
            weights['historical'] * historical_confidence +
            weights['market'] * market_confidence +
            weights['volatility'] * sample_confidence
        )
        
        return max(0.0, min(1.0, confidence))
    
    def _analyze_trend(self, prices: List[float]) -> str:
        """Analiza la tendencia de precios."""
        if not prices or len(prices) < 2:
            return 'stable'
            
        # Calcular cambio porcentual
        changes = np.diff(prices) / prices[:-1]
        avg_change = np.mean(changes)
        
        if avg_change > 0.05:
            return 'up'
        elif avg_change < -0.05:
            return 'down'
        return 'stable'
    
    def _calculate_seasonality(
        self,
        origin: str,
        destination: str,
        market_data: Dict
    ) -> float:
        """Calcula el factor de estacionalidad."""
        current_month = datetime.now().month
        seasonal_factors = market_data.get('seasonal_factors', {})
        return seasonal_factors.get(str(current_month), 0.5)
    
    def _analyze_competition(self, market_data: Dict) -> float:
        """Analiza el nivel de competencia en el mercado."""
        competitors = market_data.get('competitors', [])
        if not competitors:
            return 0.5
            
        active_competitors = len([c for c in competitors if c['active']])
        return min(1.0, active_competitors / 10.0)
    
    def _calculate_recency_factor(self, dates: List[datetime]) -> float:
        """Calcula el factor de recencia de los datos históricos."""
        if not dates:
            return 0.0
            
        now = datetime.now()
        days_old = [(now - date).days for date in dates]
        recency_scores = [1.0 / (1.0 + day/30.0) for day in days_old]
        return np.mean(recency_scores)
    
    def _calculate_confidence_level(
        self,
        sample_size: int,
        success_rate: float,
        recency_factor: float
    ) -> float:
        """Calcula el nivel de confianza basado en datos históricos."""
        size_factor = min(1.0, sample_size / 10.0)
        return size_factor * success_rate * recency_factor
    
    def _adjust_weights(
        self,
        market_condition: MarketCondition,
        historical_impact: HistoricalImpact
    ) -> Dict[str, float]:
        """Ajusta los pesos basado en la calidad de los datos."""
        # Ajustar peso histórico
        historical_quality = (
            historical_impact.sample_size / 10.0 *
            historical_impact.recency_factor
        )
        adjusted_historical = self.weight_historical * historical_quality
        
        # Ajustar peso de mercado
        market_quality = 1.0 - market_condition.volatility
        adjusted_market = self.weight_market * market_quality
        
        # Ajustar peso de volatilidad
        volatility_weight = self.weight_volatility
        
        # Normalizar pesos
        total = adjusted_historical + adjusted_market + volatility_weight
        
        return {
            'historical': adjusted_historical / total,
            'market': adjusted_market / total,
            'volatility': volatility_weight / total
        }
    
    def _calculate_market_impact(self, condition: MarketCondition) -> float:
        """Calcula el impacto basado en condiciones de mercado."""
        trend_factor = {
            'up': 1.2,
            'down': 0.8,
            'stable': 1.0
        }.get(condition.trend, 1.0)
        
        market_score = (
            condition.demand * 0.4 +
            condition.seasonality * 0.3 +
            (1.0 - condition.competition_level) * 0.3
        )
        
        return market_score * trend_factor
    
    def _calculate_volatility_adjustment(self, volatility: float) -> float:
        """Calcula el ajuste basado en volatilidad."""
        return max(0.0, 1.0 - volatility)
