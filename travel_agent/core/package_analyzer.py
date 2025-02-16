"""
Analizador de paquetes turísticos.

Este módulo se encarga de:
1. Analizar paquetes de diferentes proveedores
2. Comparar precios y características
3. Calcular puntuaciones
4. Generar recomendaciones
"""

from typing import List, Dict, Any
from datetime import datetime
import logging

from ..memory.supabase import SupabaseMemory
from .config import config
from .schemas import TravelPackage, PackageAnalysis, Recommendation


class PackageAnalyzer:
    """Analizador de paquetes turísticos."""

    def __init__(self):
        """Inicializar analizador."""
        self.logger = logging.getLogger(__name__)
        self.memory = SupabaseMemory()

    async def analyze_package(
        self, package: TravelPackage, criteria: Dict[str, Any]
    ) -> PackageAnalysis:
        """
        Analizar un paquete turístico.

        Args:
            package: Paquete a analizar
            criteria: Criterios de búsqueda del cliente

        Returns:
            Análisis del paquete
        """
        try:
            # Calcular puntuación base
            base_score = self._calculate_base_score(package)

            # Aplicar criterios específicos
            criteria_score = self._apply_criteria(package, criteria)

            # Buscar histórico de precios
            price_history = await self._get_price_history(package)
            price_score = self._analyze_price(package, price_history)

            # Analizar servicios incluidos
            services_score = self._analyze_services(package)

            # Calcular puntuación final
            final_score = (
                base_score * 0.3
                + criteria_score * 0.3
                + price_score * 0.2
                + services_score * 0.2
            )

            return PackageAnalysis(
                package_id=package.id,
                score=final_score,
                price_analysis={
                    "current_price": package.price,
                    "historical_avg": (
                        sum(price_history) / len(price_history)
                        if price_history
                        else package.price
                    ),
                    "price_trend": self._calculate_price_trend(price_history),
                },
                criteria_match=criteria_score,
                services_analysis=self._get_services_summary(package),
                recommendations=self._generate_recommendations(package, final_score),
            )

        except Exception as e:
            self.logger.error(f"Error analizando paquete {package.id}: {str(e)}")
            raise

    def _calculate_base_score(self, package: TravelPackage) -> float:
        """Calcular puntuación base del paquete."""
        score = 0.0

        # Evaluar proveedor
        if package.provider in ["OLA", "AERO"]:  # Proveedores preferidos
            score += 0.2

        # Evaluar disponibilidad
        if package.availability > 0.7:
            score += 0.2

        # Evaluar duración
        if 7 <= package.duration <= 14:  # Duración ideal
            score += 0.2

        # Evaluar temporada
        if self._is_high_season(package.start_date):
            score += 0.2

        # Evaluar servicios básicos
        basic_services = {"alojamiento", "traslados", "desayuno"}
        included = set(package.included_services)
        if basic_services.issubset(included):
            score += 0.2

        return score

    def _apply_criteria(
        self, package: TravelPackage, criteria: Dict[str, Any]
    ) -> float:
        """Aplicar criterios específicos del cliente."""
        score = 0.0
        total_criteria = len(criteria)

        for key, value in criteria.items():
            if key == "budget":
                if package.price <= value:
                    score += 1
            elif key == "destination":
                if package.destination.lower() == value.lower():
                    score += 1
            elif key == "dates":
                if (
                    package.start_date >= value["start"]
                    and package.end_date <= value["end"]
                ):
                    score += 1
            elif key == "services":
                required = set(value)
                included = set(package.included_services)
                if required.issubset(included):
                    score += 1

        return score / total_criteria if total_criteria > 0 else 0.0

    async def _get_price_history(self, package: TravelPackage) -> List[float]:
        """Obtener histórico de precios."""
        try:
            history = await self.memory.get_price_history(
                package_id=package.id, provider=package.provider
            )
            return [item["price"] for item in history]
        except Exception as e:
            self.logger.error(f"Error obteniendo histórico de precios: {str(e)}")
            return []

    def _analyze_price(
        self, package: TravelPackage, price_history: List[float]
    ) -> float:
        """Analizar precio del paquete."""
        if not price_history:
            return 0.5  # Puntuación neutral si no hay histórico

        avg_price = sum(price_history) / len(price_history)

        if package.price <= avg_price * 0.9:  # 10% o más bajo que promedio
            return 1.0
        elif package.price <= avg_price:
            return 0.8
        elif package.price <= avg_price * 1.1:  # Hasta 10% más alto
            return 0.6
        else:
            return 0.4

    def _analyze_services(self, package: TravelPackage) -> float:
        """Analizar servicios incluidos."""
        premium_services = {
            "all inclusive",
            "spa",
            "excursiones",
            "seguro",
            "asistencia 24h",
        }

        included = set(package.included_services)
        premium_count = len(premium_services.intersection(included))

        return min(1.0, premium_count / 3)  # Máximo 1.0 con 3 servicios premium

    def _calculate_price_trend(self, price_history: List[float]) -> str:
        """Calcular tendencia de precios."""
        if len(price_history) < 2:
            return "estable"

        last_prices = price_history[-3:]  # Últimos 3 precios
        if len(last_prices) < 2:
            return "estable"

        avg_change = sum(
            (b - a) / a for a, b in zip(last_prices[:-1], last_prices[1:])
        ) / (len(last_prices) - 1)

        if avg_change <= -0.05:
            return "bajando"
        elif avg_change >= 0.05:
            return "subiendo"
        else:
            return "estable"

    def _get_services_summary(self, package: TravelPackage) -> Dict[str, Any]:
        """Obtener resumen de servicios."""
        return {
            "included": package.included_services,
            "excluded": package.excluded_services,
            "premium_count": len(
                [
                    s
                    for s in package.included_services
                    if s in {"all inclusive", "spa", "excursiones"}
                ]
            ),
        }

    def _generate_recommendations(
        self, package: TravelPackage, score: float
    ) -> List[Recommendation]:
        """Generar recomendaciones para el paquete."""
        recommendations = []

        # Recomendar si es buena oportunidad
        if score >= 0.8:
            recommendations.append(
                Recommendation(
                    type="opportunity",
                    priority="alta",
                    message="Excelente oportunidad - precio y características ideales",
                )
            )

        # Recomendar si el precio está subiendo
        price_trend = self._calculate_price_trend(
            await self._get_price_history(package)
        )
        if price_trend == "subiendo":
            recommendations.append(
                Recommendation(
                    type="price",
                    priority="alta",
                    message="Reservar pronto - precios están subiendo",
                )
            )

        # Recomendar servicios adicionales
        if len(package.included_services) < 5:
            recommendations.append(
                Recommendation(
                    type="services",
                    priority="media",
                    message="Considerar agregar servicios adicionales",
                )
            )

        return recommendations

    def _is_high_season(self, date: datetime) -> bool:
        """Determinar si es temporada alta."""
        month = date.month
        return month in {1, 2, 7, 8, 12}  # Temporada alta
