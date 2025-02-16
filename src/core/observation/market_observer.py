"""Market observation and analysis system."""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from src.core.database.base import db
from src.core.models.travel import TravelPackage, PriceHistory, MarketAnalysis
from src.core.cache.redis_cache import cache

class MarketObserver:
    """System for observing and analyzing market trends."""
    
    async def track_package(self, package: TravelPackage) -> None:
        """Track a package's price and availability."""
        with db.get_session() as session:
            # Record price history
            history = PriceHistory(
                package_id=package.id,
                price=package.price,
                currency=package.currency
            )
            session.add(history)
    
    async def analyze_route(
        self,
        origin: str,
        destination: str
    ) -> Optional[Dict]:
        """Analyze market conditions for a route."""
        cache_key = f"market_analysis:{origin}:{destination}"
        
        # Try to get from cache first
        cached = await cache.get(cache_key)
        if cached:
            return cached
        
        with db.get_session() as session:
            # Get recent packages for this route
            recent_packages = session.query(TravelPackage).filter(
                TravelPackage.origin == origin,
                TravelPackage.destination == destination,
                TravelPackage.created_at >= datetime.utcnow() - timedelta(days=30)
            ).all()
            
            if not recent_packages:
                return None
            
            # Calculate metrics
            prices = [p.price for p in recent_packages]
            analysis = MarketAnalysis(
                origin=origin,
                destination=destination,
                avg_price=sum(prices) / len(prices),
                min_price=min(prices),
                max_price=max(prices),
                demand_score=self._calculate_demand(recent_packages),
                trend=self._determine_trend(recent_packages)
            )
            session.add(analysis)
            
            result = {
                "avg_price": analysis.avg_price,
                "min_price": analysis.min_price,
                "max_price": analysis.max_price,
                "demand_score": analysis.demand_score,
                "trend": analysis.trend,
                "analysis_date": datetime.utcnow().isoformat()
            }
            
            # Cache the results
            await cache.set(cache_key, result, ttl=3600)  # Cache for 1 hour
            return result
    
    def _calculate_demand(self, packages: List[TravelPackage]) -> float:
        """Calculate demand score based on availability and price changes."""
        if not packages:
            return 0.0
            
        # Simple demand calculation
        total_availability = sum(p.availability for p in packages)
        avg_availability = total_availability / len(packages)
        
        # Lower availability = higher demand
        demand_score = 1.0 - (avg_availability / 100)  # Assuming max availability is 100
        return max(0.0, min(1.0, demand_score))
    
    def _determine_trend(self, packages: List[TravelPackage]) -> str:
        """Determine price trend."""
        if not packages:
            return "stable"
            
        # Sort by creation date
        sorted_packages = sorted(packages, key=lambda p: p.created_at)
        
        if len(sorted_packages) < 2:
            return "stable"
            
        # Compare average prices from first and second half
        mid = len(sorted_packages) // 2
        first_half_avg = sum(p.price for p in sorted_packages[:mid]) / mid
        second_half_avg = sum(p.price for p in sorted_packages[mid:]) / (len(sorted_packages) - mid)
        
        # Determine trend based on price difference
        diff_percent = (second_half_avg - first_half_avg) / first_half_avg * 100
        
        if diff_percent > 5:
            return "up"
        elif diff_percent < -5:
            return "down"
        else:
            return "stable"

# Global observer instance
market_observer = MarketObserver()
