"""
Optimizador de precios.

Este módulo implementa:
1. Optimización de precios
2. Análisis de rentabilidad
3. Ajuste por temporada
4. Predicción de demanda
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import logging
import asyncio
from dataclasses import dataclass
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from prometheus_client import Counter, Histogram, REGISTRY

from smart_travel_agency.core.schemas import (
    TravelPackage,
    OptimizationResult,
    PricingStrategy,
    DemandForecast,
)
from smart_travel_agency.core.metrics import get_metrics_collector

# Métricas
metrics = get_metrics_collector("price_optimizer")

# Configurar métricas
metrics.record_operation("optimization_operations")

optimization_time = metrics.record_time(
    "optimization_time", 0.0, module="price_optimizer"
)  # Se actualizará en el método optimize


@dataclass
class PriceFactors:
    """Factores que influyen en el precio."""

    base_cost: float
    margin: float
    seasonality: float
    demand: float
    competition: float
    quality: float
    flexibility: float


class PriceOptimizer:
    """
    Optimizador de precios.

    Responsabilidades:
    1. Optimizar precios
    2. Analizar rentabilidad
    3. Predecir demanda
    4. Ajustar por temporada
    """

    def __init__(self):
        """Inicializar optimizador."""
        self.logger = logging.getLogger(__name__)

        # Configuración
        self.config = {
            "min_margin": 0.15,
            "max_margin": 0.40,
            "seasonality_window": 30,
            "demand_window": 90,
            "competition_weight": 0.3,
            "quality_weight": 0.2,
            "demand_weight": 0.3,
            "seasonality_weight": 0.2,
            "strategies": {
                "competitive": {"margin": 0.2, "weight": 0.4},
                "demand": {"elasticity": 0.3, "weight": 0.3},
                "value": {"premium": 0.1, "weight": 0.3},
            },
            "min_samples": 30,
        }

        # Cache de factores estacionales
        self.seasonality_cache = {
            "Test City": {"summer": 1.2, "winter": 0.8, "spring": 1.0, "fall": 0.9}
        }

        # Modelo de demanda
        self.model = RandomForestRegressor(
            n_estimators=100,
            random_state=42,
            max_features="sqrt",  # Fijar max_features para reproducibilidad
            bootstrap=True,  # Habilitar bootstrap para reproducibilidad
            n_jobs=1,  # Usar un solo thread para reproducibilidad
        )

        # Cache de demanda
        self.demand_cache = {}

        # Métricas
        self.metrics = get_metrics_collector("price_optimizer")

    async def optimize_price(
        self, package: TravelPackage, strategy: Optional[PricingStrategy] = None
    ) -> OptimizationResult:
        """Optimizar precio de un paquete.

        Args:
            package: Paquete a optimizar
            strategy: Estrategia de optimización

        Returns:
            Resultado de optimización

        Raises:
            ValueError: Si el paquete es None o la estrategia es inválida
        """
        try:
            if package is None:
                raise ValueError("El paquete no puede ser None")

            # Obtener factores
            factors = await self._extract_price_factors(package)

            # Seleccionar estrategia
            if strategy is None:
                strategy = self._select_strategy(package)

            # Calcular precio óptimo según estrategia
            start_time = datetime.now()
            if strategy.type == "competitive":
                optimal_price = await self._competitive_pricing(
                    package, package.total_price, factors
                )
            elif strategy.type == "value":
                optimal_price = await self._value_based_pricing(
                    package, package.total_price, factors
                )
            else:  # dynamic
                optimal_price = await self._dynamic_pricing(
                    package, package.total_price, factors
                )

            # Calcular margen y ROI
            margin = (optimal_price - factors.base_cost) / optimal_price
            roi = (optimal_price - factors.base_cost) / factors.base_cost

            # Crear metadata
            duration = datetime.now() - start_time
            metadata = {
                "strategy": strategy.type,
                "timestamp": datetime.now().isoformat(),
                "duration": str(duration.total_seconds()),
            }

            return OptimizationResult(
                original_price=package.total_price,
                optimized_price=optimal_price,
                margin=margin,
                roi=roi,
                factors={
                    "base_cost": factors.base_cost,
                    "margin": factors.margin,
                    "seasonality": factors.seasonality,
                    "demand": factors.demand,
                    "competition": factors.competition,
                    "quality": factors.quality,
                    "flexibility": factors.flexibility,
                },
                metadata=metadata,
            )

        except Exception as e:
            self.logger.error(f"Error optimizando precio: {str(e)}")
            raise

    async def optimize_prices(
        self, packages: List[TravelPackage]
    ) -> Dict[str, OptimizationResult]:
        """Optimizar precios para una lista de paquetes.

        Args:
            packages: Lista de paquetes a optimizar

        Returns:
            Diccionario con id del paquete y resultado de optimización
        """
        try:
            if not packages:
                raise ValueError("La lista de paquetes no puede estar vacía")

            optimized_prices = {}

            for package in packages:
                try:
                    if package is None:
                        continue

                    result = await self.optimize_price(package)
                    optimized_prices[package.id] = result

                except Exception as e:
                    self.logger.error(
                        f"Error optimizando precio para {package.id}: {str(e)}"
                    )
                    continue

            return optimized_prices

        except Exception as e:
            self.logger.error(f"Error optimizando precios: {str(e)}")
            raise

    async def forecast_demand(
        self,
        destination: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> DemandForecast:
        """Pronosticar demanda.

        Args:
            destination: Destino
            start_date: Fecha inicial
            end_date: Fecha final (opcional)

        Returns:
            Pronóstico de demanda

        Raises:
            ValueError: Si las fechas son inválidas o el destino es None/vacío
        """
        try:
            if not destination or destination.strip() == "":
                raise ValueError("El destino no puede estar vacío")

            # Verificar si son strings y convertir a datetime
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date)
            if end_date and isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date)

            # Si no hay end_date, usar start_date + 30 días
            if not end_date:
                end_date = start_date + timedelta(days=30)

            # Validar fechas
            if end_date < start_date:
                raise ValueError("La fecha final debe ser posterior a la fecha inicial")

            # Obtener datos históricos
            historical = await self._get_historical_data(
                destination, start_date, end_date
            )

            # Si no hay datos históricos, retornar forecast con confianza 0
            if not historical:
                self.logger.warning(f"No hay datos históricos para {destination}")
                return DemandForecast(
                    destination=destination,
                    start_date=start_date,
                    end_date=end_date,
                    daily_demand=[(start_date, 0.0)],
                    confidence=0.0,
                    metadata={
                        "training_samples": 0,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

            # Preparar datos
            X = []
            y = []
            for entry in historical:
                features = [
                    entry["date"].month,
                    entry["date"].weekday(),
                    entry["price"],
                    entry["seasonality"],
                ]
                X.append(features)
                y.append(entry["demand"])

            # Fijar semilla para reproducibilidad
            np.random.seed(42)

            # Entrenar modelo con validación cruzada
            from sklearn.model_selection import cross_val_score

            cv_scores = cross_val_score(self.model, X, y, cv=5)
            confidence = float(
                np.clip(np.mean(cv_scores), 0, 1)
            )  # Asegurar entre 0 y 1

            # Entrenar modelo final con todos los datos
            self.model.set_params(random_state=42)  # Fijar semilla del modelo
            self.model.fit(X, y)

            # Generar predicciones diarias
            daily_demand = []
            current_date = start_date
            while current_date <= end_date:
                features = [
                    current_date.month,
                    current_date.weekday(),
                    np.mean([entry["price"] for entry in historical]),
                    await self._calculate_seasonality_factor(destination, current_date),
                ]
                demand = float(self.model.predict([features])[0])
                daily_demand.append((current_date, demand))
                current_date += timedelta(days=1)

            return DemandForecast(
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                daily_demand=daily_demand,
                confidence=confidence,
                metadata={
                    "training_samples": len(historical),
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except ValueError as ve:
            self.logger.error(f"Error de validación en forecast_demand: {str(ve)}")
            raise
        except Exception as e:
            self.logger.error(f"Error en forecast_demand: {str(e)}")
            raise

    async def get_seasonality_factor(self, date: datetime, destination: str) -> float:
        """
        Obtener factor de estacionalidad.

        Args:
            date: Fecha
            destination: Destino

        Returns:
            Factor de estacionalidad
        """
        try:
            # Verificar si es string y convertir a datetime
            if isinstance(date, str):
                date = datetime.fromisoformat(date)

            # Obtener temporada
            month = date.month
            if month in [12, 1, 2]:
                season = "2"  # Verano
            elif month in [3, 4, 5]:
                season = "3"  # Otoño
            elif month in [6, 7, 8]:
                season = "4"  # Invierno
            else:
                season = "1"  # Primavera

            # Verificar cache
            cache_key = f"{destination}_{season}"
            if destination in self.seasonality_cache:
                if cache_key in self.seasonality_cache[destination]:
                    return self.seasonality_cache[destination][cache_key]

            # Obtener datos históricos
            data = await self._get_historical_data(destination, date)

            if not data:
                return 1.0

            # Calcular factor promedio
            factors = [item["seasonality"] for item in data]
            factor = float(np.mean(factors))

            # Guardar en cache
            if destination not in self.seasonality_cache:
                self.seasonality_cache[destination] = {}
            self.seasonality_cache[destination][cache_key] = factor

            return factor

        except Exception as e:
            logging.error(f"Error calculando estacionalidad: {str(e)}")
            raise

    async def _calculate_seasonality_factor(
        self, destination: str, check_in: datetime
    ) -> float:
        """Calcular factor de estacionalidad.

        Args:
            destination: Destino
            check_in: Fecha de check-in

        Returns:
            Factor de estacionalidad (0-1)
        """
        try:
            # Verificar si es string y convertir a datetime
            if isinstance(check_in, str):
                check_in = datetime.fromisoformat(check_in)

            # Obtener temporada
            month = check_in.month
            if month in [12, 1, 2]:
                season = "2"  # Verano
            elif month in [3, 4, 5]:
                season = "3"  # Otoño
            elif month in [6, 7, 8]:
                season = "4"  # Invierno
            else:
                season = "1"  # Primavera

            # Verificar cache
            cache_key = f"{destination}_{season}"
            if destination in self.seasonality_cache:
                if cache_key in self.seasonality_cache[destination]:
                    return self.seasonality_cache[destination][cache_key]

            # Obtener datos históricos
            data = await self._get_historical_data(destination, check_in)

            if not data:
                return 1.0

            # Calcular factor promedio
            factors = [item["seasonality"] for item in data]
            factor = float(np.mean(factors))

            # Guardar en cache
            if destination not in self.seasonality_cache:
                self.seasonality_cache[destination] = {}
            self.seasonality_cache[destination][cache_key] = factor

            return factor

        except Exception as e:
            self.logger.error(f"Error calculando estacionalidad: {str(e)}")
            raise

    async def _competitive_pricing(
        self, package: TravelPackage, base_price: float, factors: PriceFactors
    ) -> float:
        """Pricing basado en competencia."""
        try:
            # Calcular margen base según calidad y competencia
            margin = factors.margin + (
                (factors.competition - 0.5) * self.config["competition_weight"]
            )
            margin = min(
                max(margin, self.config["min_margin"]), self.config["max_margin"]
            )

            # Calcular precio óptimo
            optimal_price = factors.base_cost * (1 + margin)

            # Ajustar según posición competitiva y calidad
            competition_factor = 1.0 + (
                (factors.competition - 0.5) * self.config["competition_weight"]
            )

            quality_factor = 1.0 + (
                (factors.quality - 0.5) * self.config["quality_weight"]
            )

            optimal_price *= competition_factor * quality_factor

            # Asegurar que esté dentro de los límites
            min_price = base_price * 1.05  # Al menos 5% más que el precio base
            max_price = factors.base_cost * (1 + self.config["max_margin"])
            return min(max(optimal_price, min_price), max_price)

        except Exception as e:
            self.logger.error(f"Error en competitive pricing: {e}")
            raise

    async def _value_based_pricing(
        self, package: TravelPackage, base_price: float, factors: PriceFactors
    ) -> float:
        """Pricing basado en valor."""
        try:
            # Calcular margen base según calidad y demanda
            margin = factors.margin + (
                (factors.demand - 0.5) * self.config["demand_weight"]
            )
            margin = min(
                max(margin, self.config["min_margin"]), self.config["max_margin"]
            )

            # Calcular precio óptimo
            optimal_price = factors.base_cost * (1 + margin)

            # Ajustar según calidad y demanda
            quality_factor = 1.0 + (
                (factors.quality - 0.5) * self.config["quality_weight"] * 2
            )

            demand_factor = 1.0 + (
                (factors.demand - 0.5) * self.config["demand_weight"]
            )

            optimal_price *= quality_factor * demand_factor

            # Asegurar que esté dentro de los límites
            min_price = base_price * 1.05  # Al menos 5% más que el precio base
            max_price = factors.base_cost * (1 + self.config["max_margin"])
            return min(max(optimal_price, min_price), max_price)

        except Exception as e:
            self.logger.error(f"Error en value pricing: {e}")
            raise

    async def _dynamic_pricing(
        self, package: TravelPackage, base_price: float, factors: PriceFactors
    ) -> float:
        """Pricing dinámico."""
        try:
            # Calcular margen base según todos los factores
            margin = factors.margin + (
                (factors.demand + factors.competition + factors.seasonality - 1.5)
                / 3
                * (self.config["max_margin"] - self.config["min_margin"])
            )
            margin = min(
                max(margin, self.config["min_margin"]), self.config["max_margin"]
            )

            # Calcular precio óptimo
            optimal_price = factors.base_cost * (1 + margin)

            # Ajustar según factores
            competition_factor = 1.0 + (
                (factors.competition - 0.5) * self.config["competition_weight"]
            )

            quality_factor = 1.0 + (
                (factors.quality - 0.5) * self.config["quality_weight"]
            )

            demand_factor = 1.0 + (
                (factors.demand - 0.5) * self.config["demand_weight"]
            )

            seasonality_factor = 1.0 + (
                (factors.seasonality - 0.5) * self.config["seasonality_weight"]
            )

            optimal_price *= (
                competition_factor * quality_factor * demand_factor * seasonality_factor
            )

            # Asegurar que esté dentro de los límites
            min_price = base_price * 1.05  # Al menos 5% más que el precio base
            max_price = factors.base_cost * (1 + self.config["max_margin"])
            return min(max(optimal_price, min_price), max_price)

        except Exception as e:
            self.logger.error(f"Error en dynamic pricing: {e}")
            raise

    async def _extract_price_factors(self, package: TravelPackage) -> PriceFactors:
        """Extraer factores de precio.

        Args:
            package: Paquete

        Returns:
            Factores de precio
        """
        try:
            if package is None:
                raise ValueError("El paquete no puede ser None")

            # Calcular costo base
            base_cost = await self._calculate_base_cost(package)

            # Calcular margen base según calidad del hotel
            quality_score = (
                package.hotel.stars / 5 + package.hotel.review_score / 10
            ) / 2
            margin = self.config["min_margin"] + (
                quality_score * (self.config["max_margin"] - self.config["min_margin"])
            )

            # Calcular factor de estacionalidad
            seasonality = await self._calculate_seasonality_factor(
                package.destination, package.check_in
            )

            # Calcular demanda
            demand_forecast = await self.forecast_demand(
                package.destination, package.check_in
            )
            demand = demand_forecast.daily_demand[0][1]  # Usar primer día

            # Obtener competidores
            competitors = await self._get_competitors(package)
            if competitors:
                # Calcular posición competitiva (0-1)
                competition = sum(
                    1 for comp in competitors if comp.total_price < package.total_price
                ) / len(competitors)
            else:
                competition = 0.5  # Posición neutral si no hay datos

            # Calcular calidad
            quality = quality_score

            # Calcular flexibilidad (0-1)
            flexibility = 0.5
            if package.cancellation_policy == "free":
                flexibility += 0.25
            if package.modification_policy == "flexible":
                flexibility += 0.25

            return PriceFactors(
                base_cost=base_cost,
                margin=margin,
                seasonality=seasonality,
                demand=demand,
                competition=competition,
                quality=quality,
                flexibility=flexibility,
            )

        except Exception as e:
            self.logger.error(f"Error extrayendo factores: {str(e)}")
            raise

    async def _get_competitors(self, package: TravelPackage) -> List[TravelPackage]:
        """Obtener paquetes competidores."""
        # TODO: Implementar búsqueda de competidores
        return []

    async def _get_historical_data(
        self,
        destination: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Obtener datos históricos.

        Args:
            destination: Destino
            start_date: Fecha inicial
            end_date: Fecha final (opcional)

        Returns:
            Lista de datos históricos
        """
        try:
            # Simular datos históricos
            dates = []
            current = start_date - timedelta(days=365)
            end = end_date if end_date else start_date
            while current <= end:
                dates.append(current)
                current += timedelta(days=1)

            # Generar datos aleatorios
            data = []
            for date in dates:
                # Calcular factor estacional
                month = date.month
                if month in [12, 1, 2]:
                    season = "2"  # Verano
                elif month in [3, 4, 5]:
                    season = "3"  # Otoño
                elif month in [6, 7, 8]:
                    season = "4"  # Invierno
                else:
                    season = "1"  # Primavera

                factors = {"1": 1.0, "2": 1.2, "3": 0.9, "4": 0.8}

                seasonality = factors[season]

                # Simular demanda
                base_demand = np.random.normal(0.5, 0.1)
                demand = base_demand * seasonality
                demand = np.clip(demand, 0, 1)

                data.append(
                    {
                        "date": date,
                        "demand": demand,
                        "seasonality": seasonality,
                        "events": np.random.randint(0, 3),
                        "price": np.random.uniform(100, 500),
                    }
                )

            return data

        except Exception as e:
            logging.error(f"Error obteniendo datos históricos: {str(e)}")
            raise

    async def _calculate_demand_score(self, destination: str, date: datetime) -> float:
        """Calcular score de demanda."""
        # TODO: Implementar cálculo de demanda
        return 0.5

    async def _calculate_base_cost(self, package: TravelPackage) -> float:
        """Calcular costo base."""
        # TODO: Implementar cálculo de costo
        return package.total_price * 0.7

    async def _count_events(self, date: datetime, destination: str) -> int:
        """Contar eventos en destino."""
        # TODO: Implementar conteo de eventos
        return 0


# Instancia global
price_optimizer = PriceOptimizer()


async def get_price_optimizer() -> PriceOptimizer:
    """Obtener instancia del optimizador."""
    return price_optimizer
