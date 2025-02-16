"""
Motor de recomendaciones para paquetes turísticos.

Este módulo se encarga de:
1. Generar recomendaciones personalizadas
2. Aprender de interacciones previas
3. Priorizar recomendaciones
4. Adaptar sugerencias según contexto
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .schemas import TravelPackage, SearchCriteria, Recommendation, PriorityLevel
from .package_analyzer import PackageAnalyzer
from ..memory.supabase import SupabaseMemory


class RecommendationEngine:
    """Motor de recomendaciones para paquetes turísticos."""

    def __init__(self):
        """Inicializar motor."""
        self.logger = logging.getLogger(__name__)
        self.memory = SupabaseMemory()
        self.analyzer = PackageAnalyzer()

        # Factores de recomendación
        self.factors = {
            "price_weight": 0.3,
            "match_weight": 0.3,
            "popularity_weight": 0.2,
            "seasonality_weight": 0.2,
        }

    async def get_recommendations(
        self, packages: List[TravelPackage], criteria: SearchCriteria, limit: int = 5
    ) -> List[Recommendation]:
        """
        Obtener recomendaciones personalizadas.

        Args:
            packages: Lista de paquetes disponibles
            criteria: Criterios de búsqueda
            limit: Número máximo de recomendaciones

        Returns:
            Lista de recomendaciones ordenadas por relevancia
        """
        try:
            recommendations = []

            # Analizar cada paquete
            for package in packages:
                # Obtener análisis del paquete
                analysis = await self.analyzer.analyze_package(
                    package=package, criteria=criteria.dict()
                )

                # Obtener datos históricos
                history = await self._get_package_history(package)

                # Calcular score de recomendación
                score = self._calculate_recommendation_score(
                    package=package,
                    analysis=analysis,
                    history=history,
                    criteria=criteria,
                )

                if score > 0.5:  # Umbral mínimo para recomendar
                    recommendation = await self._create_recommendation(
                        package=package, score=score, analysis=analysis
                    )
                    recommendations.append(recommendation)

            # Ordenar y limitar recomendaciones
            recommendations = sorted(
                recommendations, key=lambda x: x.metadata["score"], reverse=True
            )

            return recommendations[:limit]

        except Exception as e:
            self.logger.error(f"Error generando recomendaciones: {str(e)}")
            raise

    async def learn_from_interaction(
        self,
        package: TravelPackage,
        interaction: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Aprender de interacciones con paquetes.

        Args:
            package: Paquete interactuado
            interaction: Tipo de interacción (view, click, purchase)
            metadata: Metadatos adicionales
        """
        try:
            await self.memory.store_interaction(
                package_id=package.id,
                interaction_type=interaction,
                metadata=metadata or {},
                timestamp=datetime.now(),
            )
        except Exception as e:
            self.logger.error(f"Error registrando interacción: {str(e)}")

    def _calculate_recommendation_score(
        self,
        package: TravelPackage,
        analysis: Dict[str, Any],
        history: Dict[str, Any],
        criteria: SearchCriteria,
    ) -> float:
        """Calcular puntuación de recomendación."""
        score = 0.0

        # Factor de precio
        price_score = self._calculate_price_score(package, criteria)
        score += price_score * self.factors["price_weight"]

        # Factor de coincidencia con criterios
        match_score = analysis["criteria_match"]
        score += match_score * self.factors["match_weight"]

        # Factor de popularidad
        popularity_score = self._calculate_popularity_score(history)
        score += popularity_score * self.factors["popularity_weight"]

        # Factor de temporada
        seasonality_score = self._calculate_seasonality_score(package)
        score += seasonality_score * self.factors["seasonality_weight"]

        return min(1.0, score)

    def _calculate_price_score(
        self, package: TravelPackage, criteria: SearchCriteria
    ) -> float:
        """Calcular puntuación basada en precio."""
        if not criteria.budget:
            return 0.8  # Puntuación neutral si no hay presupuesto

        # Calcular qué tan cerca está del presupuesto
        price_ratio = package.price / criteria.budget

        if price_ratio <= 0.8:  # 20% o más bajo que presupuesto
            return 1.0
        elif price_ratio <= 1.0:  # Dentro de presupuesto
            return 0.8
        elif price_ratio <= 1.2:  # Hasta 20% sobre presupuesto
            return 0.5
        else:
            return 0.2

    def _calculate_popularity_score(self, history: Dict[str, Any]) -> float:
        """Calcular puntuación basada en popularidad."""
        views = history.get("views", 0)
        clicks = history.get("clicks", 0)
        purchases = history.get("purchases", 0)

        # Pesos para cada tipo de interacción
        view_weight = 0.2
        click_weight = 0.3
        purchase_weight = 0.5

        # Normalizar valores
        max_views = 1000
        max_clicks = 100
        max_purchases = 10

        normalized_score = (
            min(1.0, views / max_views) * view_weight
            + min(1.0, clicks / max_clicks) * click_weight
            + min(1.0, purchases / max_purchases) * purchase_weight
        )

        return normalized_score

    def _calculate_seasonality_score(self, package: TravelPackage) -> float:
        """Calcular puntuación basada en temporada."""
        month = package.start_date.month

        # Definir temporadas
        high_season = {1, 2, 7, 8, 12}  # Verano y vacaciones
        shoulder_season = {3, 6, 9, 11}  # Temporadas intermedias
        low_season = {4, 5, 10}  # Temporada baja

        if month in high_season:
            return 1.0
        elif month in shoulder_season:
            return 0.7
        else:
            return 0.5

    async def _get_package_history(self, package: TravelPackage) -> Dict[str, Any]:
        """Obtener historial de interacciones con el paquete."""
        try:
            return await self.memory.get_package_history(package.id)
        except Exception as e:
            self.logger.error(f"Error obteniendo historial: {str(e)}")
            return {"views": 0, "clicks": 0, "purchases": 0}

    async def _create_recommendation(
        self, package: TravelPackage, score: float, analysis: Dict[str, Any]
    ) -> Recommendation:
        """Crear objeto de recomendación."""
        # Determinar prioridad
        priority = self._get_priority_level(score)

        # Generar mensaje
        message = self._generate_recommendation_message(
            package=package, score=score, analysis=analysis
        )

        return Recommendation(
            type="package",
            priority=priority,
            message=message,
            metadata={"package_id": package.id, "score": score, "analysis": analysis},
        )

    def _get_priority_level(self, score: float) -> PriorityLevel:
        """Determinar nivel de prioridad basado en score."""
        if score >= 0.8:
            return PriorityLevel.ALTA
        elif score >= 0.6:
            return PriorityLevel.MEDIA
        else:
            return PriorityLevel.BAJA

    def _generate_recommendation_message(
        self, package: TravelPackage, score: float, analysis: Dict[str, Any]
    ) -> str:
        """Generar mensaje de recomendación."""
        # Base del mensaje
        message = f"Recomendamos {package.title} a {package.destination}"

        # Agregar razón principal
        if analysis["price_analysis"]["price_trend"] == "bajando":
            message += " - ¡Precios están bajando!"
        elif score >= 0.8:
            message += " - ¡Excelente opción!"
        elif package.availability <= 0.3:
            message += " - ¡Últimos lugares disponibles!"

        return message
