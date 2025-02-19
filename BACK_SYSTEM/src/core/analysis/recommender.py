"""Recommendation engine for travel packages."""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..providers import TravelPackage
from .analyzer import PackageAnalyzer, PackageScore

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    """Recommendation with explanation."""

    package: TravelPackage
    score: float
    explanation: str
    alternatives: List[TravelPackage]
    comparison: Dict[str, str]


class RecommendationEngine:
    """Engine for generating travel package recommendations."""

    def __init__(
        self, analyzer: Optional[PackageAnalyzer] = None, max_alternatives: int = 3
    ):
        """Initialize recommendation engine.

        Args:
            analyzer: Optional custom package analyzer
            max_alternatives: Maximum number of alternative recommendations
        """
        self.analyzer = analyzer or PackageAnalyzer()
        self.max_alternatives = max_alternatives

    def get_recommendations(
        self,
        packages: List[TravelPackage],
        preferred_airlines: Optional[List[str]] = None,
        budget: Optional[float] = None,
    ) -> List[Recommendation]:
        """Generate recommendations from available packages.

        Args:
            packages: List of available packages
            preferred_airlines: Optional list of preferred airlines
            budget: Optional maximum budget

        Returns:
            List of recommendations with explanations
        """
        if not packages:
            return []

        # Analyze packages
        scored_packages = self.analyzer.analyze_packages(packages, preferred_airlines)

        # Filter by budget if specified
        if budget is not None:
            scored_packages = [
                sp for sp in scored_packages if sp.package.price <= budget
            ]

        recommendations = []
        for score in scored_packages[: self.max_alternatives]:
            recommendation = self._create_recommendation(score, scored_packages, budget)
            recommendations.append(recommendation)

        return recommendations

    def _create_recommendation(
        self,
        score: PackageScore,
        all_scores: List[PackageScore],
        budget: Optional[float],
    ) -> Recommendation:
        """Create a detailed recommendation for a package."""
        package = score.package
        alternatives = self._find_alternatives(score, all_scores)

        explanation = self._generate_explanation(score, budget)
        comparison = self._generate_comparison(score, alternatives)

        return Recommendation(
            package=package,
            score=score.total_score,
            explanation=explanation,
            alternatives=[alt.package for alt in alternatives],
            comparison=comparison,
        )

    def _find_alternatives(
        self, score: PackageScore, all_scores: List[PackageScore]
    ) -> List[PackageScore]:
        """Find alternative packages similar to the recommended one."""
        # Filter out the current package
        others = [s for s in all_scores if s.package.id != score.package.id]

        # Find packages with similar characteristics
        similar = []
        for other in others:
            if self._is_similar_package(score.package, other.package):
                similar.append(other)

        # Sort by score and return top alternatives
        similar.sort(key=lambda x: x.total_score, reverse=True)
        return similar[: self.max_alternatives]

    def _generate_explanation(
        self, score: PackageScore, budget: Optional[float]
    ) -> str:
        """Generate human-readable explanation for recommendation."""
        package = score.package
        details = score.details

        explanation_parts = []

        # Price analysis
        if budget:
            price_percent = (package.price / budget) * 100
            explanation_parts.append(
                f"This option is {price_percent:.1f}% of your budget"
            )

        # Duration and stops
        stops = len(package.details.get("stops", []))
        if stops == 0:
            explanation_parts.append("Direct flight")
        else:
            explanation_parts.append(f"{stops} stop{'s' if stops > 1 else ''}")

        # Convenience factors
        if package.details.get("baggage_allowance"):
            explanation_parts.append("Includes baggage")
        if package.details.get("refundable", False):
            explanation_parts.append("Refundable ticket")

        # Scoring highlights
        if score.price_score > 0.8:
            explanation_parts.append("Excellent price")
        if score.convenience_score > 0.8:
            explanation_parts.append("Very convenient")
        if score.reliability_score > 0.8:
            explanation_parts.append("Highly reliable")

        return " • ".join(explanation_parts)

    def _generate_comparison(
        self, score: PackageScore, alternatives: List[PackageScore]
    ) -> Dict[str, str]:
        """Generate comparison with alternative options."""
        comparison = {}

        if not alternatives:
            return comparison

        # Price comparison
        min_price = min(alt.package.price for alt in alternatives)
        price_diff = score.package.price - min_price
        if price_diff > 0:
            comparison["price"] = f"${price_diff:.2f} more than cheapest alternative"
        else:
            comparison["price"] = "Best price option"

        # Duration comparison
        pkg_duration = self.analyzer._get_duration_minutes(score.package)
        alt_durations = [
            self.analyzer._get_duration_minutes(alt.package) for alt in alternatives
        ]
        min_duration = min(alt_durations)
        duration_diff = pkg_duration - min_duration

        if duration_diff > 0:
            hours = duration_diff // 60
            minutes = duration_diff % 60
            if hours > 0:
                comparison["duration"] = (
                    f"{hours}h {minutes}m longer than fastest alternative"
                )
            else:
                comparison["duration"] = f"{minutes}m longer than fastest alternative"
        else:
            comparison["duration"] = "Fastest option"

        return comparison

    @staticmethod
    def _is_similar_package(pkg1: TravelPackage, pkg2: TravelPackage) -> bool:
        """Check if two packages are similar enough to be alternatives."""
        # Same route
        if pkg1.origin != pkg2.origin or pkg1.destination != pkg2.destination:
            return False

        # Similar departure time (within 12 hours)
        dep1 = pkg1.departure_date
        dep2 = pkg2.departure_date
        if abs(dep1 - dep2).total_seconds() > 43200:  # 12 hours
            return False

        # Similar price (within 30%)
        price_diff = abs(pkg1.price - pkg2.price)
        avg_price = (pkg1.price + pkg2.price) / 2
        if price_diff / avg_price > 0.3:
            return False

        return True
