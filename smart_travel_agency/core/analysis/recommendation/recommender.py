"""
Motor de recomendaciones.

Este módulo implementa:
1. Generación de recomendaciones
2. Análisis de preferencias
3. Filtrado colaborativo
4. Ranking de alternativas
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from prometheus_client import Counter, Histogram, REGISTRY

from smart_travel_agency.core.schemas import (
    TravelPackage,
    Hotel,
    CustomerProfile,
    PackageVector,
    RecommendationScore,
    Recommendation,
)
from smart_travel_agency.core.metrics import get_metrics_collector

# Métricas
metrics = get_metrics_collector("recommendation_engine")


class RecommendationEngine:
    """
    Motor de recomendaciones.

    Responsabilidades:
    1. Generar recomendaciones
    2. Analizar preferencias
    3. Rankear alternativas
    4. Filtrar opciones
    """

    def __init__(self):
        """Inicializar motor."""
        self.logger = logging.getLogger(__name__)
        self.metrics = metrics

        # Configuración
        self.config = {
            "min_similarity": 0.6,
            "max_recommendations": 5,
            "price_weight": 0.3,
            "quality_weight": 0.2,
            "location_weight": 0.2,
            "amenities_weight": 0.15,
            "activities_weight": 0.15,
        }

        # Escalador
        self.scaler = StandardScaler()

        # Cache de vectores
        self.vector_cache: Dict[str, PackageVector] = {}

    async def generate_recommendations(
        self,
        profile: CustomerProfile,
        current_package: Optional[TravelPackage] = None,
        available_packages: Optional[List[TravelPackage]] = None,
    ) -> List[Recommendation]:
        """
        Generar recomendaciones.

        Args:
            profile: Perfil del cliente
            current_package: Paquete actual
            available_packages: Paquetes disponibles

        Returns:
            Lista de recomendaciones
        """
        try:
            start_time = datetime.now()

            # Registrar operación
            self.metrics.record_operation(
                "recommendation_requests_total", request_type="personalized"
            )

            if not available_packages:
                available_packages = await self._fetch_packages(profile)

            if not available_packages:
                raise ValueError("No hay paquetes disponibles")

            # Vectorizar paquetes
            package_vectors = await self._vectorize_packages(available_packages)

            # Calcular scores
            if current_package:
                # Recomendaciones similares
                recommendations = await self._find_similar_packages(
                    current_package, available_packages, package_vectors
                )

            else:
                # Recomendaciones basadas en perfil
                recommendations = await self._rank_by_profile(
                    profile, available_packages, package_vectors
                )

            # Registrar tiempo
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.record_time("recommendation_generation_seconds", duration)

            return recommendations[: self.config["max_recommendations"]]

        except Exception as e:
            self.logger.error(f"Error generando recomendaciones: {e}")
            raise

    async def update_profile(
        self, profile: CustomerProfile, interaction: Dict[str, Any]
    ) -> CustomerProfile:
        """
        Actualizar perfil según interacción.

        Args:
            profile: Perfil actual
            interaction: Datos de interacción

        Returns:
            Perfil actualizado
        """
        try:
            # Registrar operación
            self.metrics.record_operation(
                "recommendation_requests_total", request_type="profile_update"
            )

            # Actualizar preferencias
            if "viewed_package" in interaction:
                await self._update_preferences(profile, interaction["viewed_package"])

            # Actualizar restricciones
            if "budget_limit" in interaction:
                profile.constraints["max_budget"] = interaction["budget_limit"]

            if "date_range" in interaction:
                profile.constraints["date_range"] = interaction["date_range"]

            # Actualizar intereses
            if "interests" in interaction:
                profile.interests.extend(interaction["interests"])
                profile.interests = list(set(profile.interests))

            return profile

        except Exception as e:
            self.logger.error(f"Error actualizando perfil: {e}")
            raise

    async def _vectorize_packages(
        self, packages: List[TravelPackage]
    ) -> Dict[str, PackageVector]:
        """Vectorizar paquetes."""
        try:
            vectors = {}

            for package in packages:
                # Verificar cache
                if package.id in self.vector_cache:
                    vectors[package.id] = self.vector_cache[package.id]
                    continue

                # Calcular scores
                price_score = await self._calculate_price_score(package)
                quality_score = await self._calculate_quality_score(package)
                location_score = await self._calculate_location_score(package)
                amenities_score = await self._calculate_amenities_score(package)
                activities_score = await self._calculate_activities_score(package)

                # Crear vector
                vector = PackageVector(
                    price_score=price_score,
                    quality_score=quality_score,
                    location_score=location_score,
                    amenities_score=amenities_score,
                    activities_score=activities_score,
                )

                vectors[package.id] = vector
                self.vector_cache[package.id] = vector

            return vectors

        except Exception as e:
            self.logger.error(f"Error vectorizando paquetes: {e}")
            raise

    async def _find_similar_packages(
        self,
        target: TravelPackage,
        candidates: List[TravelPackage],
        vectors: Dict[str, PackageVector],
    ) -> List[Recommendation]:
        """Encontrar paquetes similares."""
        try:
            # Obtener vector objetivo
            target_vector = vectors[target.id]

            # Calcular similitudes
            similarities = []
            for package in candidates:
                if package.id == target.id:
                    continue

                vector = vectors[package.id]

                similarity = cosine_similarity(
                    [self._vector_to_array(target_vector)],
                    [self._vector_to_array(vector)],
                )[0][0]

                if similarity >= self.config["min_similarity"]:
                    similarities.append((package, similarity))

            # Ordenar por similitud
            similarities.sort(key=lambda x: x[1], reverse=True)

            # Crear recomendaciones
            recommendations = []
            for package, similarity in similarities:
                score = await self._calculate_recommendation_score(
                    package, vectors[package.id], similarity
                )

                recommendations.append(
                    Recommendation(
                        package=package,
                        score=score,
                        reason="Similar al paquete seleccionado",
                        metadata={
                            "similarity": similarity,
                            "timestamp": datetime.now(),
                        },
                    )
                )

            return recommendations

        except Exception as e:
            self.logger.error(f"Error buscando similares: {e}")
            raise

    async def _rank_by_profile(
        self,
        profile: CustomerProfile,
        packages: List[TravelPackage],
        vectors: Dict[str, PackageVector],
    ) -> List[Recommendation]:
        """Rankear según perfil."""
        try:
            recommendations = []

            for package in packages:
                # Verificar restricciones
                if not await self._meets_constraints(package, profile):
                    continue

                # Calcular match con intereses
                interest_match = await self._calculate_interest_match(package, profile)

                # Obtener vector
                vector = vectors[package.id]

                # Calcular score
                score = await self._calculate_recommendation_score(
                    package, vector, interest_match
                )

                # Agregar recomendación
                recommendations.append(
                    Recommendation(
                        package=package,
                        score=score,
                        reason="Coincide con tus preferencias",
                        metadata={
                            "interest_match": interest_match,
                            "timestamp": datetime.now(),
                        },
                    )
                )

            # Ordenar por score
            recommendations.sort(key=lambda x: x.score.total_score, reverse=True)

            return recommendations

        except Exception as e:
            self.logger.error(f"Error rankeando por perfil: {e}")
            raise

    async def _calculate_recommendation_score(
        self, package: TravelPackage, vector: PackageVector, base_score: float
    ) -> RecommendationScore:
        """Calcular score de recomendación."""
        try:
            # Obtener optimizador
            from smart_travel_agency.core.analysis.price_optimizer.optimizer import (
                get_price_optimizer,
            )

            optimizer = await get_price_optimizer()

            # Calcular componentes
            price_score = vector.price_score * self.config["price_weight"]
            quality_score = vector.quality_score * self.config["quality_weight"]
            location_score = vector.location_score * self.config["location_weight"]
            amenities_score = vector.amenities_score * self.config["amenities_weight"]
            activities_score = (
                vector.activities_score * self.config["activities_weight"]
            )

            # Ajustar por temporada
            seasonality = await optimizer.get_seasonality_factor(
                package.check_in, package.destination
            )

            # Calcular total
            total_score = (
                base_score * 0.4
                + (
                    price_score
                    + quality_score
                    + location_score
                    + amenities_score
                    + activities_score
                )
                * 0.6
            ) * seasonality

            return RecommendationScore(
                total_score=total_score,
                components={
                    "base_score": base_score,
                    "price_score": price_score,
                    "quality_score": quality_score,
                    "location_score": location_score,
                    "amenities_score": amenities_score,
                    "activities_score": activities_score,
                    "seasonality": seasonality,
                },
            )

        except Exception as e:
            self.logger.error(f"Error calculando score: {e}")
            raise

    def _vector_to_array(self, vector: PackageVector) -> np.ndarray:
        """Convertir vector a array."""
        return np.array(
            [
                vector.price_score,
                vector.quality_score,
                vector.location_score,
                vector.amenities_score,
                vector.activities_score,
            ]
        )

    async def _fetch_packages(self, profile: CustomerProfile) -> List[TravelPackage]:
        """Obtener paquetes disponibles."""
        # TODO: Implementar búsqueda de paquetes
        return []

    async def _update_preferences(
        self, profile: CustomerProfile, package: TravelPackage
    ) -> None:
        """Actualizar preferencias."""
        # TODO: Implementar actualización
        pass

    async def _meets_constraints(
        self, package: TravelPackage, profile: CustomerProfile
    ) -> bool:
        """Verificar restricciones."""
        # TODO: Implementar validación
        return True

    async def _calculate_interest_match(
        self, package: TravelPackage, profile: CustomerProfile
    ) -> float:
        """Calcular match con intereses."""
        # TODO: Implementar cálculo
        return 0.5

    async def _calculate_price_score(self, package: TravelPackage) -> float:
        """Calcular score de precio."""
        # TODO: Implementar cálculo
        return 0.5

    async def _calculate_quality_score(self, package: TravelPackage) -> float:
        """Calcular score de calidad."""
        # TODO: Implementar cálculo
        return 0.5

    async def _calculate_location_score(self, package: TravelPackage) -> float:
        """Calcular score de ubicación."""
        # TODO: Implementar cálculo
        return 0.5

    async def _calculate_amenities_score(self, package: TravelPackage) -> float:
        """Calcular score de amenities."""
        # TODO: Implementar cálculo
        return 0.5

    async def _calculate_activities_score(self, package: TravelPackage) -> float:
        """Calcular score de actividades."""
        # TODO: Implementar cálculo
        return 0.5


# Instancia global
recommendation_engine = RecommendationEngine()


async def get_recommendation_engine() -> RecommendationEngine:
    """Obtener instancia del motor."""
    return recommendation_engine
