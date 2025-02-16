"""
Motor de análisis del agente de viajes.

Este módulo se encarga de:
1. Analizar datos de viajes
2. Procesar información de mercado
3. Generar insights
4. Evaluar tendencias
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from .schemas import (
    TravelPackage,
    SearchCriteria,
    MarketTrend,
    PackageAnalysis,
    InsightType,
)
from ..memory.supabase import SupabaseMemory


class AnalysisEngine:
    """Motor de análisis del agente de viajes."""

    def __init__(self):
        """Inicializar motor."""
        self.logger = logging.getLogger(__name__)
        self.memory = SupabaseMemory()

        # Configuración de análisis
        self.analysis_config = {
            "price_weight": 0.3,
            "popularity_weight": 0.2,
            "seasonality_weight": 0.2,
            "availability_weight": 0.3,
        }

        # Umbrales de análisis
        self.thresholds = {
            "price_variance": 0.15,  # 15% de variación
            "demand_threshold": 0.7,  # 70% de demanda
            "trend_confidence": 0.8,  # 80% de confianza
        }

    async def analyze_package(
        self, package: TravelPackage, criteria: Optional[SearchCriteria] = None
    ) -> PackageAnalysis:
        """
        Analizar paquete turístico.

        Args:
            package: Paquete a analizar
            criteria: Criterios de búsqueda

        Returns:
            Análisis del paquete
        """
        try:
            # Obtener datos históricos
            history = await self._get_package_history(package)

            # Analizar precio
            price_analysis = await self._analyze_price(package=package, history=history)

            # Analizar demanda
            demand_analysis = await self._analyze_demand(
                package=package, history=history
            )

            # Analizar temporada
            season_analysis = await self._analyze_seasonality(package=package)

            # Calcular score
            score = self._calculate_package_score(
                price_analysis=price_analysis,
                demand_analysis=demand_analysis,
                season_analysis=season_analysis,
                criteria=criteria,
            )

            # Generar insights
            insights = await self._generate_insights(
                package=package,
                price_analysis=price_analysis,
                demand_analysis=demand_analysis,
                season_analysis=season_analysis,
            )

            # Crear análisis
            analysis = PackageAnalysis(
                package_id=package.id,
                timestamp=datetime.now(),
                score=score,
                price_analysis=price_analysis,
                demand_analysis=demand_analysis,
                season_analysis=season_analysis,
                insights=insights,
            )

            # Almacenar análisis
            await self._store_analysis(analysis)

            return analysis

        except Exception as e:
            self.logger.error(f"Error analizando paquete: {str(e)}")
            raise

    async def analyze_market_trends(
        self, packages: List[TravelPackage]
    ) -> List[MarketTrend]:
        """
        Analizar tendencias de mercado.

        Args:
            packages: Lista de paquetes

        Returns:
            Lista de tendencias detectadas
        """
        try:
            trends = []

            # Agrupar paquetes por destino
            destinations = {}
            for package in packages:
                if package.destination not in destinations:
                    destinations[package.destination] = []
                destinations[package.destination].append(package)

            # Analizar tendencias por destino
            for destination, dest_packages in destinations.items():
                # Analizar precios
                price_trend = await self._analyze_price_trend(dest_packages)

                # Analizar demanda
                demand_trend = await self._analyze_demand_trend(dest_packages)

                # Analizar disponibilidad
                availability_trend = await self._analyze_availability_trend(
                    dest_packages
                )

                # Crear tendencia
                if any([price_trend, demand_trend, availability_trend]):
                    trend = MarketTrend(
                        destination=destination,
                        timestamp=datetime.now(),
                        price_trend=price_trend,
                        demand_trend=demand_trend,
                        availability_trend=availability_trend,
                        confidence=self._calculate_trend_confidence(
                            price_trend=price_trend,
                            demand_trend=demand_trend,
                            availability_trend=availability_trend,
                        ),
                    )
                    trends.append(trend)

            # Almacenar tendencias
            await self._store_trends(trends)

            return trends

        except Exception as e:
            self.logger.error(f"Error analizando tendencias: {str(e)}")
            raise

    async def get_insights(
        self, package_id: str, insight_type: Optional[InsightType] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtener insights de paquete.

        Args:
            package_id: ID del paquete
            insight_type: Tipo específico de insight

        Returns:
            Lista de insights
        """
        try:
            # Obtener análisis del paquete
            analysis = await self._get_package_analysis(package_id)
            if not analysis:
                return []

            # Filtrar por tipo si se especifica
            if insight_type:
                return [
                    insight
                    for insight in analysis.insights
                    if insight["type"] == insight_type
                ]

            return analysis.insights

        except Exception as e:
            self.logger.error(f"Error obteniendo insights: {str(e)}")
            raise

    async def _get_package_history(self, package: TravelPackage) -> Dict[str, Any]:
        """Obtener historial del paquete."""
        try:
            return await self.memory.get_package_history(package.id)

        except Exception as e:
            self.logger.error(f"Error obteniendo historial: {str(e)}")
            return {}

    async def _analyze_price(
        self, package: TravelPackage, history: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analizar precio del paquete."""
        try:
            price_history = history.get("prices", [])

            if not price_history:
                return {
                    "current_price": package.price,
                    "price_trend": "estable",
                    "price_variance": 0.0,
                    "is_competitive": True,
                }

            # Calcular tendencia
            prices = [p["price"] for p in price_history]
            avg_price = sum(prices) / len(prices)
            price_variance = abs(package.price - avg_price) / avg_price

            # Determinar tendencia
            if price_variance > self.thresholds["price_variance"]:
                if package.price > avg_price:
                    trend = "subiendo"
                else:
                    trend = "bajando"
            else:
                trend = "estable"

            return {
                "current_price": package.price,
                "average_price": avg_price,
                "price_trend": trend,
                "price_variance": price_variance,
                "is_competitive": package.price <= avg_price,
            }

        except Exception as e:
            self.logger.error(f"Error analizando precio: {str(e)}")
            return {}

    async def _analyze_demand(
        self, package: TravelPackage, history: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analizar demanda del paquete."""
        try:
            interactions = history.get("interactions", [])

            if not interactions:
                return {
                    "demand_level": "media",
                    "popularity_score": 0.5,
                    "conversion_rate": 0.0,
                }

            # Calcular métricas
            views = sum(1 for i in interactions if i["type"] == "view")
            clicks = sum(1 for i in interactions if i["type"] == "click")
            purchases = sum(1 for i in interactions if i["type"] == "purchase")

            # Calcular tasas
            click_rate = clicks / views if views > 0 else 0
            conversion_rate = purchases / clicks if clicks > 0 else 0

            # Calcular score de popularidad
            popularity_score = (
                0.3 * (views / 100)  # Normalizado a 100 views
                + 0.3 * click_rate
                + 0.4 * conversion_rate
            )

            # Determinar nivel de demanda
            if popularity_score >= self.thresholds["demand_threshold"]:
                demand_level = "alta"
            elif popularity_score >= self.thresholds["demand_threshold"] / 2:
                demand_level = "media"
            else:
                demand_level = "baja"

            return {
                "demand_level": demand_level,
                "popularity_score": popularity_score,
                "views": views,
                "clicks": clicks,
                "purchases": purchases,
                "click_rate": click_rate,
                "conversion_rate": conversion_rate,
            }

        except Exception as e:
            self.logger.error(f"Error analizando demanda: {str(e)}")
            return {}

    async def _analyze_seasonality(self, package: TravelPackage) -> Dict[str, Any]:
        """Analizar temporada del paquete."""
        try:
            month = package.start_date.month

            # Definir temporadas
            high_season = {1, 2, 7, 8, 12}  # Verano y vacaciones
            shoulder_season = {3, 6, 9, 11}  # Temporadas intermedias
            low_season = {4, 5, 10}  # Temporada baja

            # Determinar temporada
            if month in high_season:
                season_type = "alta"
                season_score = 1.0
            elif month in shoulder_season:
                season_type = "media"
                season_score = 0.7
            else:
                season_type = "baja"
                season_score = 0.5

            return {
                "season_type": season_type,
                "season_score": season_score,
                "is_high_season": month in high_season,
                "month": month,
            }

        except Exception as e:
            self.logger.error(f"Error analizando temporada: {str(e)}")
            return {}

    def _calculate_package_score(
        self,
        price_analysis: Dict[str, Any],
        demand_analysis: Dict[str, Any],
        season_analysis: Dict[str, Any],
        criteria: Optional[SearchCriteria] = None,
    ) -> float:
        """Calcular score del paquete."""
        try:
            # Score de precio
            price_score = 1.0 if price_analysis.get("is_competitive", True) else 0.5

            # Score de demanda
            demand_score = demand_analysis.get("popularity_score", 0.5)

            # Score de temporada
            season_score = season_analysis.get("season_score", 0.5)

            # Calcular score final
            score = (
                price_score * self.analysis_config["price_weight"]
                + demand_score * self.analysis_config["popularity_weight"]
                + season_score * self.analysis_config["seasonality_weight"]
            )

            # Ajustar por criterios si existen
            if criteria:
                score = self._adjust_score_by_criteria(score, criteria)

            return min(1.0, score)

        except Exception as e:
            self.logger.error(f"Error calculando score: {str(e)}")
            return 0.5

    async def _generate_insights(
        self,
        package: TravelPackage,
        price_analysis: Dict[str, Any],
        demand_analysis: Dict[str, Any],
        season_analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generar insights del paquete."""
        insights = []

        try:
            # Insights de precio
            if price_analysis.get("price_trend") == "bajando":
                insights.append(
                    {
                        "type": InsightType.PRICE,
                        "message": "Precios están bajando",
                        "importance": "alta",
                    }
                )

            # Insights de demanda
            if demand_analysis.get("demand_level") == "alta":
                insights.append(
                    {
                        "type": InsightType.DEMAND,
                        "message": "Alta demanda detectada",
                        "importance": "alta",
                    }
                )

            # Insights de temporada
            if season_analysis.get("is_high_season"):
                insights.append(
                    {
                        "type": InsightType.SEASONALITY,
                        "message": "Temporada alta",
                        "importance": "media",
                    }
                )

            return insights

        except Exception as e:
            self.logger.error(f"Error generando insights: {str(e)}")
            return []

    async def _store_analysis(self, analysis: PackageAnalysis):
        """Almacenar análisis en base de conocimiento."""
        try:
            await self.memory.store_package_analysis(analysis.dict())

        except Exception as e:
            self.logger.error(f"Error almacenando análisis: {str(e)}")
            raise

    async def _store_trends(self, trends: List[MarketTrend]):
        """Almacenar tendencias en base de conocimiento."""
        try:
            for trend in trends:
                await self.memory.store_market_trend(trend.dict())

        except Exception as e:
            self.logger.error(f"Error almacenando tendencias: {str(e)}")
            raise

    async def _get_package_analysis(self, package_id: str) -> Optional[PackageAnalysis]:
        """Obtener análisis de paquete."""
        try:
            analysis = await self.memory.get_package_analysis(package_id)
            if analysis:
                return PackageAnalysis(**analysis)
            return None

        except Exception as e:
            self.logger.error(f"Error obteniendo análisis: {str(e)}")
            return None

    def _adjust_score_by_criteria(
        self, score: float, criteria: SearchCriteria
    ) -> float:
        """Ajustar score según criterios."""
        try:
            adjustments = []

            # Ajuste por presupuesto
            if criteria.budget:
                price_adjustment = min(
                    1.0, criteria.budget / criteria.price if criteria.price > 0 else 1.0
                )
                adjustments.append(price_adjustment)

            # Ajuste por fechas
            if criteria.start_date and criteria.end_date:
                date_match = 1.0  # Implementar lógica de fechas
                adjustments.append(date_match)

            # Aplicar ajustes
            if adjustments:
                return score * (sum(adjustments) / len(adjustments))

            return score

        except Exception as e:
            self.logger.error(f"Error ajustando score: {str(e)}")
            return score
