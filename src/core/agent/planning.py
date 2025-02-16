"""Sistema de planificación del agente."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json

from src.core.database.base import db
from src.core.models.travel import TravelPackage, MarketAnalysis
from src.core.agent.analysis import analysis_system
from src.core.cache.redis_cache import cache

class ActionType(Enum):
    """Tipos de acciones recomendadas."""
    PURCHASE = "purchase"
    SELL = "sell"
    ADJUST_PRICE = "adjust_price"
    MONITOR = "monitor"
    INVESTIGATE = "investigate"
    HOLD = "hold"

class PriorityLevel(Enum):
    """Niveles de prioridad."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class Action:
    """Acción recomendada."""
    type: ActionType
    priority: PriorityLevel
    route: tuple
    description: str
    expected_impact: float  # Impacto esperado en porcentaje
    deadline: datetime
    context: Dict[str, Any]

@dataclass
class Plan:
    """Plan estratégico."""
    route: tuple
    market_status: str
    risk_level: str
    actions: List[Action]
    estimated_profit: float
    confidence: float
    valid_until: datetime
    metadata: Dict[str, Any]

class PlanningSystem:
    """Sistema de planificación estratégica."""
    
    def __init__(self):
        self._active_plans: Dict[str, Plan] = {}
    
    async def create_plan(
        self,
        origin: str,
        destination: str,
        timeframe_days: int = 7
    ) -> Optional[Plan]:
        """Crear un plan estratégico para una ruta."""
        route_key = f"{origin}-{destination}"
        cache_key = f"route_plan:{route_key}"
        
        # Intentar obtener del caché
        cached_plan = await cache.get(cache_key)
        if cached_plan:
            return Plan(**json.loads(cached_plan))
        
        # Obtener análisis de mercado
        insight = await analysis_system.analyze_route(
            origin,
            destination,
            days=30
        )
        
        if not insight:
            return None
        
        # Determinar estado del mercado
        market_status = self._evaluate_market_status(insight)
        
        # Evaluar nivel de riesgo
        risk_level = self._evaluate_risk_level(insight)
        
        # Generar acciones recomendadas
        actions = self._generate_actions(
            insight,
            market_status,
            risk_level,
            timeframe_days
        )
        
        # Estimar beneficio potencial
        estimated_profit = self._estimate_profit(insight, actions)
        
        # Crear plan
        plan = Plan(
            route=(origin, destination),
            market_status=market_status,
            risk_level=risk_level,
            actions=actions,
            estimated_profit=estimated_profit,
            confidence=insight.confidence,
            valid_until=datetime.utcnow() + timedelta(days=timeframe_days),
            metadata={
                "price_trend": insight.price_trend,
                "demand_trend": insight.demand_trend,
                "volatility": insight.price_volatility,
                "avg_price": insight.supporting_data["avg_price"],
                "creation_date": datetime.utcnow().isoformat()
            }
        )
        
        # Guardar en caché
        try:
            # Convertir a dict excluyendo campos no serializables
            plan_dict = {
                "route": plan.route,
                "market_status": plan.market_status,
                "risk_level": plan.risk_level,
                "actions": [
                    {
                        "type": a.type.value,
                        "priority": a.priority.value,
                        "route": a.route,
                        "description": a.description,
                        "expected_impact": a.expected_impact,
                        "deadline": a.deadline.isoformat(),
                        "context": a.context
                    }
                    for a in plan.actions
                ],
                "estimated_profit": plan.estimated_profit,
                "confidence": plan.confidence,
                "valid_until": plan.valid_until.isoformat(),
                "metadata": plan.metadata
            }
            await cache.set(cache_key, json.dumps(plan_dict), ttl=3600)
        except Exception:
            # Log error pero no fallar
            pass
        
        return plan
    
    def _evaluate_market_status(self, insight) -> str:
        """Evaluar estado general del mercado."""
        if insight.price_volatility > 15:
            return "volatile"
        elif insight.price_trend in ["strongly_bullish", "strongly_bearish"]:
            return "trending"
        elif insight.seasonality == "highly_seasonal":
            return "seasonal"
        elif insight.price_trend == "neutral" and insight.demand_trend == "stable":
            return "stable"
        return "developing"
    
    def _evaluate_risk_level(self, insight) -> str:
        """Evaluar nivel de riesgo."""
        risk_score = 0
        
        # Factor: Volatilidad
        if insight.price_volatility > 20:
            risk_score += 3
        elif insight.price_volatility > 10:
            risk_score += 2
        elif insight.price_volatility > 5:
            risk_score += 1
        
        # Factor: Tendencia de precios
        if insight.price_trend in ["strongly_bullish", "strongly_bearish"]:
            risk_score += 2
        elif insight.price_trend in ["bullish", "bearish"]:
            risk_score += 1
        
        # Factor: Demanda
        if insight.demand_trend in ["very_high", "very_low"]:
            risk_score += 2
        elif insight.demand_trend in ["high", "low"]:
            risk_score += 1
        
        # Factor: Confianza
        if insight.confidence < 0.3:
            risk_score += 2
        elif insight.confidence < 0.5:
            risk_score += 1
        
        # Determinar nivel
        if risk_score >= 7:
            return "very_high"
        elif risk_score >= 5:
            return "high"
        elif risk_score >= 3:
            return "medium"
        return "low"
    
    def _generate_actions(
        self,
        insight,
        market_status: str,
        risk_level: str,
        timeframe_days: int
    ) -> List[Action]:
        """Generar acciones recomendadas."""
        actions = []
        now = datetime.utcnow()
        
        # Acción basada en recomendación principal
        if insight.recommendation == "strong_buy":
            actions.append(Action(
                type=ActionType.PURCHASE,
                priority=PriorityLevel.HIGH,
                route=insight.route,
                description="Adquirir paquetes aprovechando precios bajos y alta demanda",
                expected_impact=10.0,
                deadline=now + timedelta(days=2),
                context={
                    "current_price": insight.supporting_data["avg_price"],
                    "demand_level": insight.demand_trend
                }
            ))
        
        elif insight.recommendation == "strong_sell":
            actions.append(Action(
                type=ActionType.SELL,
                priority=PriorityLevel.HIGH,
                route=insight.route,
                description="Vender paquetes antes de posible caída de precios",
                expected_impact=8.0,
                deadline=now + timedelta(days=2),
                context={
                    "current_price": insight.supporting_data["avg_price"],
                    "price_trend": insight.price_trend
                }
            ))
        
        # Acciones basadas en estado del mercado
        if market_status == "volatile":
            actions.append(Action(
                type=ActionType.MONITOR,
                priority=PriorityLevel.CRITICAL,
                route=insight.route,
                description="Monitorear mercado cada 2 horas por alta volatilidad",
                expected_impact=5.0,
                deadline=now + timedelta(days=timeframe_days),
                context={
                    "volatility": insight.price_volatility,
                    "check_frequency": "2h"
                }
            ))
        
        elif market_status == "seasonal":
            actions.append(Action(
                type=ActionType.ADJUST_PRICE,
                priority=PriorityLevel.MEDIUM,
                route=insight.route,
                description="Ajustar precios según patrón estacional",
                expected_impact=6.0,
                deadline=now + timedelta(days=3),
                context={
                    "seasonality": insight.seasonality,
                    "current_price": insight.supporting_data["avg_price"]
                }
            ))
        
        # Acciones basadas en nivel de riesgo
        if risk_level in ["high", "very_high"]:
            actions.append(Action(
                type=ActionType.INVESTIGATE,
                priority=PriorityLevel.HIGH,
                route=insight.route,
                description="Investigar factores causantes del alto riesgo",
                expected_impact=4.0,
                deadline=now + timedelta(days=1),
                context={
                    "risk_level": risk_level,
                    "volatility": insight.price_volatility
                }
            ))
        
        return actions
    
    def _estimate_profit(self, insight, actions: List[Action]) -> float:
        """Estimar beneficio potencial del plan."""
        total_impact = sum(action.expected_impact for action in actions)
        confidence_factor = insight.confidence
        
        # Ajustar por volatilidad
        volatility_factor = max(0.5, 1 - (insight.price_volatility / 100))
        
        return total_impact * confidence_factor * volatility_factor

# Instancia global
planning_system = PlanningSystem()
