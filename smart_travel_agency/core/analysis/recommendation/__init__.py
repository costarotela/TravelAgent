"""Módulo de recomendaciones."""

from .recommender import get_recommendation_engine, RecommendationEngine, PackageVector

__all__ = [
    'get_recommendation_engine',
    'RecommendationEngine',
    'PackageVector'
]
