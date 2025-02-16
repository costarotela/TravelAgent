"""Package analyzer for evaluating and scoring travel options."""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from ..providers import TravelPackage

logger = logging.getLogger(__name__)


@dataclass
class PackageScore:
    """Score and analysis details for a travel package."""
    package: TravelPackage
    total_score: float
    price_score: float
    duration_score: float
    convenience_score: float
    reliability_score: float
    details: Dict[str, float]


class PackageAnalyzer:
    """Analyzer for evaluating and scoring travel packages."""

    def __init__(
        self,
        price_weight: float = 0.3,
        duration_weight: float = 0.2,
        convenience_weight: float = 0.3,
        reliability_weight: float = 0.2
    ):
        """Initialize package analyzer with scoring weights.
        
        Args:
            price_weight: Weight for price score (0-1)
            duration_weight: Weight for duration score (0-1)
            convenience_weight: Weight for convenience score (0-1)
            reliability_weight: Weight for reliability score (0-1)
        """
        self._validate_weights(
            price_weight,
            duration_weight,
            convenience_weight,
            reliability_weight
        )
        self.price_weight = price_weight
        self.duration_weight = duration_weight
        self.convenience_weight = convenience_weight
        self.reliability_weight = reliability_weight

    def analyze_packages(
        self,
        packages: List[TravelPackage],
        preferred_airlines: Optional[List[str]] = None
    ) -> List[PackageScore]:
        """Analyze and score a list of travel packages.
        
        Args:
            packages: List of packages to analyze
            preferred_airlines: Optional list of preferred airlines
        
        Returns:
            List of PackageScore objects, sorted by total score
        """
        if not packages:
            return []

        # Calculate base metrics for normalization
        price_range = self._get_price_range(packages)
        duration_range = self._get_duration_range(packages)

        # Score each package
        scores = []
        for package in packages:
            try:
                score = self._score_package(
                    package,
                    price_range,
                    duration_range,
                    preferred_airlines
                )
                scores.append(score)
            except Exception as e:
                logger.error(f"Error scoring package {package.id}: {e}")
                continue

        # Sort by total score, descending
        return sorted(scores, key=lambda x: x.total_score, reverse=True)

    def _score_package(
        self,
        package: TravelPackage,
        price_range: Tuple[float, float],
        duration_range: Tuple[int, int],
        preferred_airlines: Optional[List[str]]
    ) -> PackageScore:
        """Score an individual package based on various criteria."""
        # Calculate individual scores
        price_score = self._calculate_price_score(package, price_range)
        duration_score = self._calculate_duration_score(package, duration_range)
        convenience_score = self._calculate_convenience_score(package)
        reliability_score = self._calculate_reliability_score(
            package,
            preferred_airlines
        )

        # Calculate weighted total
        total_score = (
            self.price_weight * price_score +
            self.duration_weight * duration_score +
            self.convenience_weight * convenience_score +
            self.reliability_weight * reliability_score
        )

        return PackageScore(
            package=package,
            total_score=total_score,
            price_score=price_score,
            duration_score=duration_score,
            convenience_score=convenience_score,
            reliability_score=reliability_score,
            details=self._get_score_details(package)
        )

    def _calculate_price_score(
        self,
        package: TravelPackage,
        price_range: Tuple[float, float]
    ) -> float:
        """Calculate normalized price score (higher is better)."""
        min_price, max_price = price_range
        if min_price == max_price:
            return 1.0
        return 1 - ((package.price - min_price) / (max_price - min_price))

    def _calculate_duration_score(
        self,
        package: TravelPackage,
        duration_range: Tuple[int, int]
    ) -> float:
        """Calculate normalized duration score (higher is better)."""
        duration = self._get_duration_minutes(package)
        min_duration, max_duration = duration_range
        if min_duration == max_duration:
            return 1.0
        return 1 - ((duration - min_duration) / (max_duration - min_duration))

    def _calculate_convenience_score(self, package: TravelPackage) -> float:
        """Calculate convenience score based on stops, time, etc."""
        score = 1.0
        
        # Penalize for stops
        stops = len(package.details.get("stops", []))
        score -= stops * 0.15  # -0.15 per stop

        # Check departure and arrival times
        dep_time = datetime.fromisoformat(package.departure_date).time()
        if dep_time.hour < 6 or dep_time.hour > 22:  # Very early or late
            score -= 0.1

        # Check baggage allowance
        if not package.details.get("baggage_allowance"):
            score -= 0.1

        # Check refundable status
        if not package.details.get("refundable", False):
            score -= 0.1

        return max(0.0, min(1.0, score))

    def _calculate_reliability_score(
        self,
        package: TravelPackage,
        preferred_airlines: Optional[List[str]]
    ) -> float:
        """Calculate reliability score based on airline and provider."""
        score = 0.8  # Base score

        # Preferred airline bonus
        if preferred_airlines and package.details.get("airline"):
            if package.details["airline"].upper() in {a.upper() for a in preferred_airlines}:
                score += 0.2

        # Provider reliability
        provider_scores = {
            "OLA": 0.1,
            "AERO": 0.1,
            "DESPEGAR": 0.1
        }
        score += provider_scores.get(package.provider, 0)

        return min(1.0, score)

    def _get_score_details(self, package: TravelPackage) -> Dict[str, float]:
        """Get detailed scoring breakdown."""
        return {
            "stops_penalty": -0.15 * len(package.details.get("stops", [])),
            "baggage_score": 0.1 if package.details.get("baggage_allowance") else 0,
            "refundable_score": 0.1 if package.details.get("refundable", False) else 0,
            "time_penalty": -0.1 if self._is_inconvenient_time(package) else 0
        }

    @staticmethod
    def _get_price_range(packages: List[TravelPackage]) -> Tuple[float, float]:
        """Get min and max prices from packages."""
        prices = [p.price for p in packages]
        return min(prices), max(prices)

    @staticmethod
    def _get_duration_range(packages: List[TravelPackage]) -> Tuple[int, int]:
        """Get min and max durations from packages."""
        durations = [PackageAnalyzer._get_duration_minutes(p) for p in packages]
        return min(durations), max(durations)

    @staticmethod
    def _get_duration_minutes(package: TravelPackage) -> int:
        """Convert package duration to minutes."""
        duration_str = package.details.get("duration", "0")
        try:
            if 'h' in duration_str and 'm' in duration_str:
                hours, minutes = duration_str.split('h')
                return int(hours.strip()) * 60 + int(minutes.strip('m').strip())
            elif 'h' in duration_str:
                hours = float(duration_str.strip('h').strip())
                return int(hours * 60)
            elif 'm' in duration_str:
                return int(duration_str.strip('m').strip())
            return int(duration_str)  # Assume minutes if no unit
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _is_inconvenient_time(package: TravelPackage) -> bool:
        """Check if package has inconvenient departure/arrival times."""
        try:
            dep_time = datetime.fromisoformat(package.departure_date).time()
            return dep_time.hour < 6 or dep_time.hour > 22
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _validate_weights(*weights: float) -> None:
        """Validate that weights sum to 1 and are between 0 and 1."""
        if not all(0 <= w <= 1 for w in weights):
            raise ValueError("All weights must be between 0 and 1")
        if abs(sum(weights) - 1.0) > 0.001:
            raise ValueError("Weights must sum to 1")
