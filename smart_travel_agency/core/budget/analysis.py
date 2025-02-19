"""
Motor de análisis de presupuestos.

Este módulo se encarga de:
1. Análisis de competitividad
2. Análisis de tendencias
3. Optimización de presupuestos
4. Generación de insights
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime
import logging
from prometheus_client import Counter, Histogram

from ..schemas import (
    Budget,
    TravelPackage,
    SearchCriteria,
    MarketTrend,
    PackageAnalysis
)
from ..memory import get_memory_manager
from ..metrics import get_metrics_collector

# Métricas
ANALYSIS_OPERATIONS = Counter(
    'budget_analysis_operations_total',
    'Number of analysis operations',
    ['operation_type']
)

ANALYSIS_LATENCY = Histogram(
    'analysis_operation_latency_seconds',
    'Latency of analysis operations',
    ['operation_type']
)

class BudgetAnalysisEngine:
    """Motor de análisis de presupuestos."""

    def __init__(self):
        """Inicializar motor."""
        self.logger = logging.getLogger(__name__)
        self.memory = get_memory_manager()
        self.metrics = get_metrics_collector()
        
        # Configuración de pesos para análisis
        self.weights = {
            "price": 0.4,
            "margin": 0.3,
            "seasonality": 0.2,
            "availability": 0.1
        }
        
        # Umbrales de análisis
        self.thresholds = {
            "price_variance": 0.15,  # 15% variación máxima
            "margin_minimum": 0.10,   # 10% margen mínimo
            "demand_threshold": 0.7,  # 70% demanda mínima
            "trend_confidence": 0.8   # 80% confianza en tendencias
        }

    async def analyze_budget(
        self,
        budget: Budget,
        criteria: Optional[SearchCriteria] = None
    ) -> Dict[str, Any]:
        """
        Analizar presupuesto completo.
        
        Args:
            budget: Presupuesto a analizar
            criteria: Criterios de búsqueda opcionales
            
        Returns:
            Análisis completo del presupuesto
        """
        try:
            start_time = datetime.now()
            
            # Análisis de competitividad
            competitiveness = await self._analyze_competitiveness(budget)
            
            # Análisis de tendencias
            trends = await self._analyze_trends(budget)
            
            # Análisis de optimización
            optimization = await self._analyze_optimization_opportunities(
                budget,
                criteria
            )
            
            # Generar insights
            insights = await self._generate_insights(
                budget,
                competitiveness,
                trends,
                optimization
            )
            
            analysis = {
                "budget_id": budget.id,
                "timestamp": datetime.now().isoformat(),
                "competitiveness": competitiveness,
                "trends": trends,
                "optimization": optimization,
                "insights": insights,
                "score": self._calculate_final_score(
                    competitiveness,
                    trends,
                    optimization
                )
            }
            
            # Registrar métricas
            duration = (datetime.now() - start_time).total_seconds()
            ANALYSIS_LATENCY.labels(
                operation_type="full_analysis"
            ).observe(duration)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analizando presupuesto: {e}")
            raise

    async def _analyze_competitiveness(
        self,
        budget: Budget
    ) -> Dict[str, Any]:
        """Analizar competitividad del presupuesto."""
        try:
            # Obtener precios del mercado
            market_prices = await self.memory.get_market_prices(
                [pkg.id for pkg in budget.packages]
            )
            
            # Calcular diferencias
            price_differences = []
            for pkg in budget.packages:
                if pkg.id in market_prices:
                    diff = (
                        (pkg.price - market_prices[pkg.id]) /
                        market_prices[pkg.id]
                    ) * 100
                    price_differences.append(diff)
            
            # Calcular márgenes
            margins = []
            for pkg in budget.packages:
                if pkg.cost_price:
                    margin = (
                        (pkg.price - pkg.cost_price) /
                        pkg.price
                    ) * 100
                    margins.append(margin)
            
            return {
                "price_difference_avg": sum(price_differences) / len(price_differences) if price_differences else 0,
                "price_difference_max": max(price_differences) if price_differences else 0,
                "margin_avg": sum(margins) / len(margins) if margins else 0,
                "margin_min": min(margins) if margins else 0,
                "is_competitive": all(
                    diff <= self.thresholds["price_variance"] * 100
                    for diff in price_differences
                ) if price_differences else False
            }
            
        except Exception as e:
            self.logger.error(f"Error analizando competitividad: {e}")
            raise

    async def _analyze_trends(
        self,
        budget: Budget
    ) -> Dict[str, Any]:
        """Analizar tendencias del mercado."""
        try:
            # Obtener tendencias históricas
            trends = await self.memory.get_market_trends(
                [pkg.id for pkg in budget.packages]
            )
            
            price_trends = []
            demand_trends = []
            
            for pkg in budget.packages:
                if pkg.id in trends:
                    pkg_trend = trends[pkg.id]
                    price_trends.append(pkg_trend["price_trend"])
                    demand_trends.append(pkg_trend["demand_trend"])
            
            return {
                "price_trend_avg": sum(price_trends) / len(price_trends) if price_trends else 0,
                "demand_trend_avg": sum(demand_trends) / len(demand_trends) if demand_trends else 0,
                "trend_confidence": self.thresholds["trend_confidence"],
                "trend_period": "30d"  # Período de análisis
            }
            
        except Exception as e:
            self.logger.error(f"Error analizando tendencias: {e}")
            raise

    async def _analyze_optimization_opportunities(
        self,
        budget: Budget,
        criteria: Optional[SearchCriteria] = None
    ) -> Dict[str, Any]:
        """Analizar oportunidades de optimización."""
        try:
            opportunities = []
            
            # Analizar márgenes bajos
            for pkg in budget.packages:
                if pkg.cost_price:
                    margin = ((pkg.price - pkg.cost_price) / pkg.price) * 100
                    if margin < self.thresholds["margin_minimum"] * 100:
                        opportunities.append({
                            "type": "low_margin",
                            "package_id": pkg.id,
                            "current_value": margin,
                            "recommended_minimum": self.thresholds["margin_minimum"] * 100
                        })
            
            # Analizar precios no competitivos
            market_prices = await self.memory.get_market_prices(
                [pkg.id for pkg in budget.packages]
            )
            
            for pkg in budget.packages:
                if pkg.id in market_prices:
                    diff = ((pkg.price - market_prices[pkg.id]) / market_prices[pkg.id]) * 100
                    if abs(diff) > self.thresholds["price_variance"] * 100:
                        opportunities.append({
                            "type": "non_competitive_price",
                            "package_id": pkg.id,
                            "current_difference": diff,
                            "recommended_maximum": self.thresholds["price_variance"] * 100
                        })
            
            # Analizar disponibilidad
            availability = await self.memory.get_packages_availability(
                [pkg.id for pkg in budget.packages]
            )
            
            for pkg in budget.packages:
                if pkg.id in availability:
                    if availability[pkg.id] < self.thresholds["demand_threshold"]:
                        opportunities.append({
                            "type": "low_availability",
                            "package_id": pkg.id,
                            "current_availability": availability[pkg.id],
                            "threshold": self.thresholds["demand_threshold"]
                        })
            
            return {
                "opportunities": opportunities,
                "opportunity_count": len(opportunities),
                "priority_score": self._calculate_opportunity_priority(opportunities)
            }
            
        except Exception as e:
            self.logger.error(f"Error analizando optimizaciones: {e}")
            raise

    async def _generate_insights(
        self,
        budget: Budget,
        competitiveness: Dict[str, Any],
        trends: Dict[str, Any],
        optimization: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generar insights basados en análisis."""
        insights = []
        
        # Insights de competitividad
        if not competitiveness["is_competitive"]:
            insights.append({
                "type": "warning",
                "category": "competitiveness",
                "message": "Precios superiores al mercado",
                "severity": "high"
            })
        
        # Insights de tendencias
        if trends["price_trend_avg"] > 5:  # 5% incremento
            insights.append({
                "type": "opportunity",
                "category": "market_trend",
                "message": "Tendencia alcista en precios",
                "severity": "medium"
            })
        
        # Insights de optimización
        if optimization["opportunity_count"] > 0:
            insights.append({
                "type": "action_required",
                "category": "optimization",
                "message": f"{optimization['opportunity_count']} oportunidades de mejora identificadas",
                "severity": "medium"
            })
        
        return insights

    def _calculate_final_score(
        self,
        competitiveness: Dict[str, Any],
        trends: Dict[str, Any],
        optimization: Dict[str, Any]
    ) -> float:
        """Calcular puntuación final del presupuesto."""
        try:
            # Componentes del score
            competitive_score = 100 - abs(competitiveness["price_difference_avg"])
            trend_score = 100 - (abs(trends["price_trend_avg"]) if trends["price_trend_avg"] < 0 else 0)
            optimization_score = 100 - (optimization["opportunity_count"] * 10)
            
            # Aplicar pesos
            final_score = (
                competitive_score * self.weights["price"] +
                trend_score * self.weights["seasonality"] +
                optimization_score * self.weights["margin"]
            )
            
            return round(max(0, min(100, final_score)), 2)
            
        except Exception as e:
            self.logger.error(f"Error calculando score final: {e}")
            return 0.0

    def _calculate_opportunity_priority(
        self,
        opportunities: List[Dict[str, Any]]
    ) -> float:
        """Calcular prioridad de oportunidades de optimización."""
        if not opportunities:
            return 0.0
            
        priorities = {
            "low_margin": 0.8,
            "non_competitive_price": 0.6,
            "low_availability": 0.4
        }
        
        total_priority = sum(
            priorities[opp["type"]] for opp in opportunities
        )
        
        return round(total_priority / len(opportunities), 2)

# Instancia global
analysis_engine = BudgetAnalysisEngine()

async def get_analysis_engine() -> BudgetAnalysisEngine:
    """Obtener instancia del motor de análisis."""
    return analysis_engine
