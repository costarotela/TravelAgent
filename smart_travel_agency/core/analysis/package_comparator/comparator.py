"""
Comparador de paquetes turísticos.

Este módulo implementa:
1. Análisis comparativo de paquetes
2. Cálculo de competitividad
3. Detección de oportunidades
4. Análisis de mercado
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np
import logging
from sklearn.preprocessing import StandardScaler
from scipy.stats import norm

from smart_travel_agency.core.schemas import (
    TravelPackage,
    Hotel,
    ComparisonResult,
    MarketAnalysis,
    CompetitivePosition
)
from smart_travel_agency.core.metrics import get_metrics_collector
from smart_travel_agency.core.analysis.price_optimizer.optimizer import get_price_optimizer

# Métricas
metrics = get_metrics_collector('package_comparator')

# Configurar métricas
metrics.record_operation(operation_name='comparison_operations')

# Tiempo de análisis
metrics.record_time(metric_name='analysis_time', value=0.0)  # Se actualizará en el método analyze_market

@dataclass
class PackageFeatures:
    """Características extraídas de un paquete."""
    price_per_night: float
    quality_score: float
    flexibility_score: float
    popularity_score: float
    seasonality_factor: float

class MarketAnalysis:
    """Análisis de mercado."""
    
    def __init__(
        self,
        price_analysis: Dict[str, float],
        quality_analysis: Dict[str, Any],
        flexibility_analysis: Dict[str, Any],
        seasonality_analysis: Dict[str, Any],
        optimal_prices: Dict[str, float],
        metadata: Dict[str, Any]
    ):
        self.price_analysis = price_analysis
        self.quality_analysis = quality_analysis
        self.flexibility_analysis = flexibility_analysis
        self.seasonality_analysis = seasonality_analysis
        self.optimal_prices = optimal_prices
        self.metadata = metadata

class PackageComparator:
    """
    Comparador de paquetes.
    
    Responsabilidades:
    1. Extraer características
    2. Comparar paquetes
    3. Analizar mercado
    4. Detectar oportunidades
    """

    def __init__(self):
        """Inicializar comparador."""
        self.logger = logging.getLogger(__name__)
        self.metrics = metrics
        
        # Configuración
        self.config = {
            "min_samples": 3,
            "seasonality_window": 30,
            "quality_weights": {
                "stars": 0.4,
                "reviews": 0.3,
                "amenities": 0.3
            },
            "flexibility_weights": {
                "cancellation": 0.5,
                "modification": 0.3,
                "payment_options": 0.2
            }
        }
        
        # Escaladores
        self.price_scaler = StandardScaler()
        self.quality_scaler = StandardScaler()
        self.flex_scaler = StandardScaler()

    async def compare_packages(
        self,
        target: TravelPackage,
        competitors: List[TravelPackage]
    ) -> ComparisonResult:
        """
        Comparar paquete con competidores.
        
        Args:
            target: Paquete objetivo
            competitors: Paquetes competidores
            
        Returns:
            Resultado de comparación
        """
        try:
            # Registrar operación
            metrics.record_operation(operation_name='comparison_operations', operation_type='direct')
            
            if len(competitors) < self.config["min_samples"]:
                raise ValueError(
                    "Insuficientes muestras para comparación"
                )
            
            # Extraer características
            target_features = await self._extract_features(target)
            comp_features = [
                await self._extract_features(p)
                for p in competitors
            ]
            
            # Calcular posición competitiva
            position = await self._calculate_position(
                target_features,
                comp_features
            )
            
            # Detectar oportunidades
            opportunities = await self._detect_opportunities(
                target,
                target_features,
                competitors,
                comp_features
            )
            
            return ComparisonResult(
                target_id=target.id,
                position=position,
                opportunities=opportunities,
                metadata={
                    "num_competitors": len(competitors),
                    "timestamp": datetime.now()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error comparando paquetes: {e}")
            raise

    async def analyze_market(
        self,
        packages: List[TravelPackage]
    ) -> MarketAnalysis:
        """
        Analizar mercado.
        
        Args:
            packages: Lista de paquetes
            
        Returns:
            Análisis de mercado
        """
        try:
            start_time = datetime.now()
            
            # Registrar operación
            metrics.record_operation(operation_name='comparison_operations', operation_type='market')
            
            if len(packages) < self.config["min_samples"]:
                raise ValueError(
                    "Insuficientes muestras para análisis"
                )
            
            # Extraer características
            features = [
                await self._extract_features(p)
                for p in packages
            ]
            
            # Análisis de precios
            prices = [p.price_per_night for p in features]
            price_stats = {
                "mean": np.mean(prices),
                "std": np.std(prices),
                "min": np.min(prices),
                "max": np.max(prices),
                "median": np.median(prices)
            }
            
            # Análisis de calidad
            quality = [p.quality_score for p in features]
            quality_stats = {
                "mean": np.mean(quality),
                "std": np.std(quality),
                "distribution": np.histogram(
                    quality,
                    bins=5
                )[0].tolist()
            }
            
            # Análisis de flexibilidad
            flexibility = [p.flexibility_score for p in features]
            flex_stats = {
                "mean": np.mean(flexibility),
                "std": np.std(flexibility),
                "distribution": np.histogram(
                    flexibility,
                    bins=5
                )[0].tolist()
            }
            
            # Análisis de estacionalidad
            seasonality = [p.seasonality_factor for p in features]
            season_stats = {
                "current_factor": np.mean(seasonality),
                "trend": np.polyfit(
                    range(len(seasonality)),
                    seasonality,
                    1
                )[0]
            }
            
            # Registrar tiempo
            duration = (datetime.now() - start_time).total_seconds()
            metrics.record_time(metric_name='analysis_time', value=duration)
            
            optimizer = await get_price_optimizer()
            
            # Análisis de precios con optimizador
            optimal_prices = await optimizer.optimize_prices(packages)
            
            return MarketAnalysis(
                price_analysis=price_stats,
                quality_analysis=quality_stats,
                flexibility_analysis=flex_stats,
                seasonality_analysis=season_stats,
                optimal_prices=optimal_prices,
                metadata={
                    "sample_size": len(packages),
                    "timestamp": datetime.now(),
                    "duration": duration
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error analizando mercado: {e}")
            raise

    async def _extract_features(self, package: TravelPackage) -> PackageFeatures:
        """Extraer características de un paquete.
        
        Args:
            package: Paquete del que extraer características
            
        Returns:
            Características del paquete
        """
        try:
            # Calcular precio por noche
            price_per_night = package.total_price / max(package.nights, 1)
            
            # Calcular puntuación de calidad (0-1)
            quality_components = [
                package.hotel.stars / 5.0 if package.hotel and package.hotel.stars else 0.5,
                package.hotel.review_score / 10.0 if package.hotel and package.hotel.review_score else 0.5,
                1.0 if package.hotel and package.hotel.amenities else 0.5
            ]
            quality_score = sum(quality_components) / len(quality_components)
            
            # Calcular puntuación de flexibilidad (0-1)
            flexibility_components = [
                1.0 if package.cancellation_policy == "free" else 0.0,
                1.0 if package.modification_policy == "flexible" else 0.0,
                min(1.0, len(package.payment_options) / 3.0) if package.payment_options else 0.0
            ]
            flexibility_score = sum(flexibility_components) / len(flexibility_components)
            
            # Calcular puntuación de popularidad (0-1)
            popularity_score = package.hotel.popularity_index if package.hotel else 0.5
            
            # Obtener factor de estacionalidad
            seasonality_factor = await self._get_seasonality_factor(
                package.destination,
                package.check_in
            )
            
            return PackageFeatures(
                price_per_night=price_per_night,
                quality_score=quality_score,
                flexibility_score=flexibility_score,
                popularity_score=popularity_score,
                seasonality_factor=seasonality_factor
            )
            
        except Exception as e:
            logging.error(f"Error extrayendo características: {str(e)}")
            raise

    async def _calculate_position(
        self,
        target: PackageFeatures,
        competitors: List[PackageFeatures]
    ) -> CompetitivePosition:
        """Calcular posición competitiva.
        
        Args:
            target: Características del paquete objetivo
            competitors: Características de paquetes competidores
            
        Returns:
            Posición competitiva
        """
        try:
            # Extraer precios
            prices = [p.price_per_night for p in competitors if p.price_per_night > 0]
            if not prices:
                return CompetitivePosition(
                    price_percentile=0.5,
                    quality_percentile=0.5,
                    flexibility_percentile=0.5,
                    position="standard"
                )
                
            # Calcular estadísticas
            avg_price = np.mean(prices)
            std_price = np.std(prices) if len(prices) > 1 else avg_price * 0.1
            
            # Calcular posición relativa
            z_score = (target.price_per_night - avg_price) / max(std_price, 1)
            
            # Normalizar a 0-1
            price_position = 1 - norm.cdf(z_score)
            
            # Calcular posición de calidad
            quality_scores = [p.quality_score for p in competitors]
            avg_quality = np.mean(quality_scores)
            std_quality = np.std(quality_scores) if len(quality_scores) > 1 else 0.1
            z_score = (target.quality_score - avg_quality) / max(std_quality, 0.1)
            quality_position = 1 - norm.cdf(z_score)
            
            # Calcular posición de flexibilidad
            flex_scores = [p.flexibility_score for p in competitors]
            avg_flex = np.mean(flex_scores)
            std_flex = np.std(flex_scores) if len(flex_scores) > 1 else 0.1
            z_score = (target.flexibility_score - avg_flex) / max(std_flex, 0.1)
            flex_position = 1 - norm.cdf(z_score)
            
            # Determinar posición
            if quality_position > 0.7:
                if price_position < 0.3:
                    position = "value_leader"
                else:
                    position = "premium"
            else:
                if price_position < 0.3:
                    position = "budget"
                else:
                    position = "standard"
            
            return CompetitivePosition(
                price_percentile=float(price_position),
                quality_percentile=float(quality_position),
                flexibility_percentile=float(flex_position),
                position=position
            )
            
        except Exception as e:
            logging.error(f"Error calculando posición: {str(e)}")
            raise

    async def _detect_opportunities(
        self,
        target: TravelPackage,
        target_features: PackageFeatures,
        competitors: List[TravelPackage],
        comp_features: List[PackageFeatures]
    ) -> List[Dict[str, Any]]:
        """Detectar oportunidades de mejora."""
        try:
            opportunities = []
            
            # Análisis de precio
            avg_price = np.mean(
                [f.price_per_night for f in comp_features]
            )
            
            if target_features.price_per_night > avg_price * 1.2:
                opportunities.append({
                    "type": "price_adjustment",
                    "description": "Precio superior al promedio del mercado",
                    "suggestion": "Considerar ajuste de precio",
                    "data": {
                        "current_price": target_features.price_per_night,
                        "market_avg": avg_price
                    }
                })
            
            # Análisis de calidad
            avg_quality = np.mean(
                [f.quality_score for f in comp_features]
            )
            
            if target_features.quality_score < avg_quality * 0.8:
                opportunities.append({
                    "type": "quality_improvement",
                    "description": "Calidad inferior al promedio",
                    "suggestion": "Mejorar amenities o servicios",
                    "data": {
                        "current_score": target_features.quality_score,
                        "market_avg": avg_quality
                    }
                })
            
            # Análisis de flexibilidad
            avg_flex = np.mean(
                [f.flexibility_score for f in comp_features]
            )
            
            if target_features.flexibility_score < avg_flex * 0.8:
                opportunities.append({
                    "type": "flexibility_improvement",
                    "description": "Menor flexibilidad que competidores",
                    "suggestion": "Revisar políticas",
                    "data": {
                        "current_score": target_features.flexibility_score,
                        "market_avg": avg_flex
                    }
                })
            
            # Análisis de estacionalidad
            if target_features.seasonality_factor > 1.2:
                opportunities.append({
                    "type": "seasonal_pricing",
                    "description": "Alta demanda estacional",
                    "suggestion": "Optimizar precio por temporada",
                    "data": {
                        "seasonality_factor": target_features.seasonality_factor
                    }
                })
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error detectando oportunidades: {e}")
            raise

    async def _get_seasonality_factor(
        self,
        destination: str,
        check_in: datetime
    ) -> float:
        """Obtener factor de estacionalidad.
        
        Args:
            destination: Destino del paquete
            check_in: Fecha de check-in
            
        Returns:
            Factor de estacionalidad
        """
        try:
            # Obtener temporada
            month = check_in.month
            if month in [12, 1, 2]:
                season = "winter"
            elif month in [3, 4, 5]:
                season = "spring"
            elif month in [6, 7, 8]:
                season = "summer"
            else:
                season = "fall"
                
            # Factores por temporada
            factors = {
                "winter": 0.8,
                "spring": 1.0,
                "summer": 1.2,
                "fall": 0.9
            }
            
            return factors[season]
            
        except Exception as e:
            logging.error(f"Error obteniendo factor estacional: {str(e)}")
            raise

# Instancia global
package_comparator = PackageComparator()

def get_package_comparator() -> PackageComparator:
    """Obtener instancia del comparador de paquetes.
    
    Returns:
        Instancia del comparador de paquetes
    """
    return PackageComparator()
