"""Travel agent implementation."""

from typing import List, Optional
from datetime import datetime

from src.core.agent.base import AgentCore
from src.core.providers.base import SearchCriteria, TravelPackage


class TravelAgent(AgentCore):
    """Simple travel agent with basic functionality."""

    async def search_packages(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """Search for travel packages."""
        await self.start_action("search_packages")

        try:
            # Simulated search for now
            packages = [
                TravelPackage(
                    id="pkg1",
                    provider="test",
                    origin=criteria.origin,
                    destination=criteria.destination,
                    departure_date=criteria.departure_date,
                    return_date=criteria.return_date,
                    price=1000.0,
                    currency="USD",
                    availability=10,
                    details={"flight": "AA123"},
                )
            ]

            # Track metrics
            await self.add_metric("results_count", len(packages))
            await self.add_metric("search_time_ms", 100)

            await self.end_action(success=True)
            return packages

        except Exception as e:
            await self.end_action(success=False, error=str(e))
            raise

    async def analyze_prices(self, packages: List[TravelPackage]) -> dict:
        """Basic price analysis."""
        await self.start_action("analyze_prices")

        try:
            prices = [p.price for p in packages]
            analysis = {
                "min_price": min(prices) if prices else 0,
                "max_price": max(prices) if prices else 0,
                "avg_price": sum(prices) / len(prices) if prices else 0,
            }

            await self.add_metric("packages_analyzed", len(packages))

            await self.end_action(success=True)
            return analysis

        except Exception as e:
            await self.end_action(success=False, error=str(e))
            raise

    def get_performance_summary(self) -> dict:
        """Get basic performance metrics."""
        return {
            "search_success_rate": self.get_success_rate("search_packages"),
            "analysis_success_rate": self.get_success_rate("analyze_prices"),
            "recent_metrics": self.get_recent_metrics(),
        }
