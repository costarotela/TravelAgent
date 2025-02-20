"""
Core scraping module with optimization support.
"""

from .base import BaseScraper, ScraperConfig, Credentials, OptimizationResult
from .change_detector import ChangeDetector, ChangeAnalyzer, ChangeImpact

__all__ = [
    "BaseScraper",
    "ScraperConfig",
    "Credentials",
    "OptimizationResult",
    "ChangeDetector",
    "ChangeAnalyzer",
    "ChangeImpact",
]
