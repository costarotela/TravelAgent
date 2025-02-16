"""Sistema de observación del agente."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pydantic import BaseModel
from src.core.database.base import db
from src.core.models.travel import TravelPackage, MarketAnalysis
from src.core.cache.redis_cache import cache

class MarketTrend(BaseModel):
    """Modelo para tendencias de mercado."""
    origin: str
    destination: str
    avg_price: float
    min_price: float
    max_price: float
    demand_score: float
    trend: str  # "up", "down", "stable"
    confidence: float
    last_updated: datetime

class ObservationSystem:
    """Sistema de observación y análisis de mercado."""
    
    def __init__(self):
        self._trends: Dict[str, MarketTrend] = {}
        self._last_analysis: Dict[str, datetime] = {}
    
    async def observe_route(
        self,
        origin: str,
        destination: str
    ) -> Optional[MarketTrend]:
        """Observar y analizar una ruta específica."""
        route_key = f"{origin}-{destination}"
        cache_key = f"market_trend:{route_key}"
        
        # Intentar obtener del caché
        cached_trend = await cache.get(cache_key)
        if cached_trend:
            return MarketTrend(**cached_trend)
        
        # Analizar datos recientes
        with db.get_session() as session:
            recent_packages = session.query(TravelPackage).filter(
                TravelPackage.origin == origin,
                TravelPackage.destination == destination,
                TravelPackage.created_at >= datetime.utcnow() - timedelta(days=30)
            ).all()
            
            if not recent_packages:
                return None
            
            # Calcular métricas
            prices = [p.price for p in recent_packages]
            trend = self._calculate_trend(recent_packages)
            demand = self._calculate_demand(recent_packages)
            confidence = self._calculate_confidence(len(recent_packages))
            
            market_trend = MarketTrend(
                origin=origin,
                destination=destination,
                avg_price=sum(prices) / len(prices),
                min_price=min(prices),
                max_price=max(prices),
                demand_score=demand,
                trend=trend,
                confidence=confidence,
                last_updated=datetime.utcnow()
            )
            
            # Guardar análisis
            analysis = MarketAnalysis(
                origin=origin,
                destination=destination,
                avg_price=market_trend.avg_price,
                min_price=market_trend.min_price,
                max_price=market_trend.max_price,
                demand_score=market_trend.demand_score,
                trend=market_trend.trend,
                data={
                    "confidence": market_trend.confidence,
                    "sample_size": len(recent_packages)
                }
            )
            session.add(analysis)
            session.commit()
            
            # Actualizar caché
            await cache.set(
                cache_key,
                market_trend.dict(),
                ttl=3600  # 1 hora
            )
            
            return market_trend
    
    def _calculate_trend(self, packages: List[TravelPackage]) -> str:
        """Calcular tendencia de precios."""
        if len(packages) < 2:
            return "stable"
        
        # Ordenar por fecha
        sorted_packages = sorted(packages, key=lambda p: p.created_at)
        
        # Comparar promedios de primera y segunda mitad
        mid = len(sorted_packages) // 2
        first_half = sorted_packages[:mid]
        second_half = sorted_packages[mid:]
        
        first_avg = sum(p.price for p in first_half) / len(first_half)
        second_avg = sum(p.price for p in second_half) / len(second_half)
        
        # Calcular cambio porcentual
        change = ((second_avg - first_avg) / first_avg) * 100
        
        if change > 5:
            return "up"
        elif change < -5:
            return "down"
        return "stable"
    
    def _calculate_demand(self, packages: List[TravelPackage]) -> float:
        """Calcular score de demanda."""
        if not packages:
            return 0.0
        
        # Factores de demanda
        availability_score = 1.0 - (
            sum(p.availability for p in packages) / 
            (len(packages) * 100)  # Asumiendo máximo de 100 por paquete
        )
        
        # Más factores pueden ser agregados aquí
        
        return min(1.0, max(0.0, availability_score))
    
    def _calculate_confidence(self, sample_size: int) -> float:
        """Calcular nivel de confianza basado en tamaño de muestra."""
        # Modelo simple: más muestras = más confianza
        base_confidence = 0.5
        sample_factor = min(1.0, sample_size / 100)  # Máximo con 100 muestras
        return base_confidence + (sample_factor * 0.5)  # Máximo 1.0

# Instancia global
observation_system = ObservationSystem()
