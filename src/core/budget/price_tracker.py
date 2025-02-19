"""Simple price tracking for budgets."""

from datetime import datetime
from typing import Dict, Optional
from src.core.database.base import db
from src.core.models.travel import TravelPackage, PriceHistory
from src.core.cache.redis_cache import cache


class PriceTracker:
    """Simple price tracking for budget creation."""

    async def track_price(self, package: TravelPackage) -> None:
        """Track package price for budget reference.

        Args:
            package: Package to track
        """
        with db.get_session() as session:
            history = PriceHistory(
                package_id=package.id, price=package.price, currency=package.currency
            )
            session.add(history)

    async def get_price_history(self, package_id: str) -> Optional[Dict]:
        """Get simple price history for a package.

        Args:
            package_id: ID of package to get history for

        Returns:
            Basic price history or None if not found
        """
        cache_key = f"price_history:{package_id}"

        # Try cache first
        cached = await cache.get(cache_key)
        if cached:
            return cached

        with db.get_session() as session:
            history = (
                session.query(PriceHistory)
                .filter(PriceHistory.package_id == package_id)
                .order_by(PriceHistory.created_at.desc())
                .limit(5)  # Solo últimos 5 registros
                .all()
            )

            if not history:
                return None

            result = {
                "current_price": history[0].price,
                "currency": history[0].currency,
                "last_updated": history[0].created_at.isoformat(),
                "recent_prices": [
                    {"price": h.price, "date": h.created_at.isoformat()}
                    for h in history
                ],
            }

            # Cache for 1 hour
            await cache.set(cache_key, result, expire=3600)
            return result
