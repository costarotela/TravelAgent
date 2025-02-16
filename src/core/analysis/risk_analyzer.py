"""Módulo para análisis avanzado de riesgo."""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime, timedelta

@dataclass
class RiskMetrics:
    """Métricas detalladas de riesgo."""
    volatility_risk: float
    market_risk: float
    operational_risk: float
    financial_risk: float
    total_risk: float
    risk_tolerance: float
    risk_capacity: float
    var_95: float  # Value at Risk 95%
    cvar_95: float  # Conditional VaR 95%

@dataclass
class RiskFactors:
    """Factores que influyen en el riesgo."""
    market_volatility: float
    competition_level: float
    demand_stability: float
    price_sensitivity: float
    operational_complexity: float
    financial_exposure: float

class RiskAnalyzer:
    """Sistema avanzado de análisis de riesgo."""
    
    def __init__(self):
        self.risk_threshold = 0.7
        self.confidence_level = 0.95
        self._risk_history = []
        
    async def analyze_risk(
        self,
        action_type: str,
        market_data: Dict,
        financial_data: Optional[Dict] = None,
        historical_data: Optional[List] = None
    ) -> Tuple[RiskMetrics, str, List[str]]:
        """Analiza el riesgo de una acción potencial."""
        # Extraer factores de riesgo
        risk_factors = self._extract_risk_factors(
            market_data,
            financial_data,
            historical_data
        )
        
        # Calcular métricas de riesgo
        risk_metrics = self._calculate_risk_metrics(
            action_type,
            risk_factors,
            historical_data
        )
        
        # Generar evaluación
        risk_level = self._evaluate_risk_level(risk_metrics)
        
        # Generar recomendaciones
        recommendations = self._generate_risk_recommendations(
            risk_metrics,
            risk_factors,
            risk_level
        )
        
        return risk_metrics, risk_level, recommendations
    
    def _extract_risk_factors(
        self,
        market_data: Dict,
        financial_data: Optional[Dict],
        historical_data: Optional[List]
    ) -> RiskFactors:
        """Extrae factores de riesgo de los datos disponibles."""
        # Analizar volatilidad del mercado
        prices = market_data.get('prices', [])
        if len(prices) > 1:
            returns = np.diff(prices) / prices[:-1]
            market_volatility = np.std(returns)
        else:
            market_volatility = 0.0
            
        # Analizar competencia
        competitors = market_data.get('competitors', [])
        active_competitors = sum(
            1 for comp in competitors 
            if comp.get('active', False)
        )
        competition_level = active_competitors / max(len(competitors), 1)
        
        # Analizar estabilidad de demanda
        demand_history = [
            d.get('demand', 0.5) 
            for d in (historical_data or [])
        ]
        demand_stability = 1.0 - np.std(demand_history) if demand_history else 0.5
        
        # Analizar sensibilidad de precios
        price_changes = np.diff(prices) if len(prices) > 1 else [0]
        demand_changes = np.diff(demand_history) if len(demand_history) > 1 else [0]
        
        if len(price_changes) == len(demand_changes) and len(price_changes) > 0:
            price_sensitivity = abs(np.corrcoef(price_changes, demand_changes)[0, 1])
        else:
            price_sensitivity = 0.5
            
        # Analizar complejidad operacional
        if financial_data:
            operational_complexity = financial_data.get('operational_complexity', 0.5)
            financial_exposure = financial_data.get('financial_exposure', 0.5)
        else:
            operational_complexity = 0.5
            financial_exposure = 0.5
            
        return RiskFactors(
            market_volatility=market_volatility,
            competition_level=competition_level,
            demand_stability=demand_stability,
            price_sensitivity=price_sensitivity,
            operational_complexity=operational_complexity,
            financial_exposure=financial_exposure
        )
    
    def _calculate_risk_metrics(
        self,
        action_type: str,
        factors: RiskFactors,
        historical_data: Optional[List]
    ) -> RiskMetrics:
        """Calcula métricas detalladas de riesgo."""
        # Calcular riesgo de volatilidad
        volatility_risk = factors.market_volatility * 0.7 + factors.price_sensitivity * 0.3
        
        # Calcular riesgo de mercado
        market_risk = (
            factors.competition_level * 0.4 +
            (1 - factors.demand_stability) * 0.4 +
            volatility_risk * 0.2
        )
        
        # Calcular riesgo operacional
        operational_risk = factors.operational_complexity
        
        # Calcular riesgo financiero
        financial_risk = factors.financial_exposure
        
        # Calcular riesgo total ponderado
        total_risk = (
            market_risk * 0.4 +
            operational_risk * 0.3 +
            financial_risk * 0.3
        )
        
        # Calcular tolerancia al riesgo
        risk_tolerance = self._calculate_risk_tolerance(
            action_type,
            historical_data
        )
        
        # Calcular capacidad de riesgo
        risk_capacity = self._calculate_risk_capacity(
            total_risk,
            risk_tolerance
        )
        
        # Calcular VaR y CVaR
        returns = self._calculate_historical_returns(historical_data)
        var_95 = np.percentile(returns, 5) if len(returns) > 0 else -0.1
        cvar_95 = np.mean(
            [r for r in returns if r <= var_95]
        ) if len(returns) > 0 else -0.15
        
        return RiskMetrics(
            volatility_risk=volatility_risk,
            market_risk=market_risk,
            operational_risk=operational_risk,
            financial_risk=financial_risk,
            total_risk=total_risk,
            risk_tolerance=risk_tolerance,
            risk_capacity=risk_capacity,
            var_95=var_95,
            cvar_95=cvar_95
        )
    
    def _calculate_risk_tolerance(
        self,
        action_type: str,
        historical_data: Optional[List]
    ) -> float:
        """Calcula la tolerancia al riesgo basada en datos históricos."""
        if not historical_data:
            return 0.5
            
        # Filtrar por tipo de acción
        relevant_data = [
            action for action in historical_data
            if action.get('type') == action_type
        ]
        
        if not relevant_data:
            return 0.5
            
        # Analizar resultados históricos
        success_rate = np.mean([
            float(action.get('success', False))
            for action in relevant_data
        ])
        
        # Ajustar tolerancia según éxito histórico
        return min(0.8, max(0.2, success_rate))
    
    def _calculate_risk_capacity(
        self,
        total_risk: float,
        risk_tolerance: float
    ) -> float:
        """Calcula la capacidad de riesgo."""
        # Ajustar capacidad según riesgo total y tolerancia
        base_capacity = 1.0 - total_risk
        return min(base_capacity * 1.2, risk_tolerance * 1.5)
    
    def _calculate_historical_returns(
        self,
        historical_data: Optional[List]
    ) -> List[float]:
        """Calcula retornos históricos para análisis VaR."""
        if not historical_data:
            return []
            
        returns = []
        for action in historical_data:
            if 'impact' in action and 'expected_impact' in action:
                actual = float(action['impact'])
                expected = float(action['expected_impact'])
                returns.append((actual - expected) / max(abs(expected), 0.001))
                
        return returns if returns else [0.0]
    
    def _evaluate_risk_level(self, metrics: RiskMetrics) -> str:
        """Evalúa el nivel de riesgo general."""
        if metrics.total_risk < 0.2:
            return "muy_bajo"
        elif metrics.total_risk < 0.4:
            return "bajo"
        elif metrics.total_risk < 0.6:
            return "medio"
        elif metrics.total_risk < 0.8:
            return "alto"
        return "muy_alto"
    
    def _generate_risk_recommendations(
        self,
        metrics: RiskMetrics,
        factors: RiskFactors,
        risk_level: str
    ) -> List[str]:
        """Genera recomendaciones basadas en el análisis de riesgo."""
        recommendations = []
        
        # Analizar componentes principales de riesgo
        if metrics.market_risk > 0.6:
            if factors.competition_level > 0.7:
                recommendations.append(
                    "Alta competencia en el mercado - considerar diferenciación"
                )
            if factors.market_volatility > 0.5:
                recommendations.append(
                    "Mercado volátil - implementar estrategias de cobertura"
                )
                
        if metrics.operational_risk > 0.6:
            recommendations.append(
                "Alto riesgo operacional - revisar procesos y controles"
            )
            
        if metrics.financial_risk > 0.6:
            recommendations.append(
                "Alto riesgo financiero - considerar reducir exposición"
            )
            
        # Analizar capacidad vs tolerancia
        if metrics.risk_capacity < metrics.risk_tolerance:
            recommendations.append(
                "Capacidad de riesgo por debajo de tolerancia - "
                "considerar reducir exposición"
            )
            
        # Analizar VaR y CVaR
        if abs(metrics.var_95) > 0.2:
            recommendations.append(
                f"VaR significativo ({metrics.var_95:.1%}) - "
                "implementar límites de pérdida"
            )
            
        # Recomendaciones generales según nivel
        if risk_level in ["alto", "muy_alto"]:
            recommendations.append(
                "Nivel de riesgo elevado - "
                "requiere aprobación y monitoreo especial"
            )
        elif risk_level == "medio":
            recommendations.append(
                "Riesgo moderado - "
                "implementar controles adicionales"
            )
            
        return recommendations
    
    def update_risk_history(
        self,
        action_type: str,
        risk_metrics: RiskMetrics,
        actual_outcome: float
    ) -> None:
        """Actualiza el histórico de riesgo con nuevos datos."""
        self._risk_history.append({
            'type': action_type,
            'metrics': risk_metrics,
            'outcome': actual_outcome,
            'timestamp': datetime.now()
        })
        
    def get_risk_stats(self) -> Dict:
        """Obtiene estadísticas del sistema de riesgo."""
        if not self._risk_history:
            return {}
            
        recent_risks = [
            h['metrics'].total_risk 
            for h in self._risk_history[-50:]
        ]
        
        return {
            'mean_risk': np.mean(recent_risks),
            'risk_volatility': np.std(recent_risks),
            'risk_trend': (
                'increasing' if np.mean(np.diff(recent_risks)) > 0
                else 'decreasing'
            ),
            'num_samples': len(self._risk_history)
        }
