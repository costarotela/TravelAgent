"""Basic package analysis for budget creation."""

from typing import Dict, List, Optional
from dataclasses import dataclass
from src.core.models.travel import TravelPackage

@dataclass
class PackageScore:
    """Basic score for a travel package."""
    package: TravelPackage
    total_score: float
    price_score: float
    availability_score: float
    details: Dict[str, float]

class PackageAnalyzer:
    """Simple analyzer for evaluating travel packages for budgets."""

    def __init__(self, price_weight: float = 0.7, availability_weight: float = 0.3):
        """Initialize package analyzer with basic weights.

        Args:
            price_weight: Weight for price score (0-1)
            availability_weight: Weight for availability score (0-1)
        """
        self._validate_weights(price_weight, availability_weight)
        self.price_weight = price_weight
        self.availability_weight = availability_weight

    def _validate_weights(self, *weights):
        """Validate that weights sum to 1."""
        if sum(weights) != 1.0:
            raise ValueError("Weights must sum to 1.0")

    def analyze_package(self, package: TravelPackage, market_avg_price: float) -> PackageScore:
        """Analyze a single package for budget creation.

        Args:
            package: Package to analyze
            market_avg_price: Average market price for similar packages

        Returns:
            Basic score and analysis
        """
        # Calculate basic scores
        price_score = self._calculate_price_score(package.price, market_avg_price)
        availability_score = self._calculate_availability_score(package)

        # Calculate total score
        total_score = (
            self.price_weight * price_score +
            self.availability_weight * availability_score
        )

        return PackageScore(
            package=package,
            total_score=total_score,
            price_score=price_score,
            availability_score=availability_score,
            details={
                "price_comparison": package.price / market_avg_price,
                "availability": package.availability if hasattr(package, "availability") else 1.0
            }
        )

    def _calculate_price_score(self, price: float, market_avg: float) -> float:
        """Calculate basic price score."""
        if market_avg <= 0:
            return 0.5
        ratio = price / market_avg
        # Lower price = higher score, capped at reasonable limits
        return min(1.0, max(0.0, 1.5 - ratio))

    def _calculate_availability_score(self, package: TravelPackage) -> float:
        """Calculate basic availability score."""
        # Simple availability check, can be expanded based on needs
        if not hasattr(package, "availability"):
            return 1.0
        return float(package.availability)
