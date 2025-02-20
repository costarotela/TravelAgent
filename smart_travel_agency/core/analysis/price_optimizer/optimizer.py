"""
Optimizador de precios para paquetes de viaje.

Este módulo implementa la lógica para:
1. Calcular precios óptimos basados en factores del mercado
2. Analizar la competencia
3. Ajustar precios según demanda y estacionalidad
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from ...schemas import TravelPackage, PricingStrategy

logger = logging.getLogger(__name__)


@dataclass
class PriceFactors:
    """Factores que influyen en el precio."""

    base_cost: Decimal
    margin: Decimal
    seasonality: Decimal
    demand: Decimal
    competition: Decimal
    quality: Decimal
    flexibility: Decimal


@dataclass
class OptimizationResult:
    """Resultado de la optimización de precio."""

    optimal_price: Decimal
    margin: Decimal
    roi: Decimal
    strategy: PricingStrategy
    metadata: Dict


class PriceOptimizer:
    """Optimizador de precios para paquetes de viaje."""

    def __init__(self):
        """Inicializa el optimizador."""
        self.default_margin = Decimal("0.15")
        self.min_margin = Decimal("0.05")
        self.max_margin = Decimal("0.35")

    async def optimize_price(
        self,
        package: TravelPackage,
        strategy: Optional[PricingStrategy] = None
    ) -> OptimizationResult:
        """
        Optimiza el precio de un paquete de viaje.
        
        Args:
            package: Paquete a optimizar
            strategy: Estrategia de precios opcional
            
        Returns:
            Resultado de la optimización
        """
        try:
            if not package:
                raise ValueError("El paquete no puede ser None")

            # Extraer factores
            factors = await self._extract_price_factors(package)
            
            # Seleccionar estrategia
            if not strategy:
                strategy = await self._select_strategy(package)

            # Calcular precio base
            optimal_price = package.total_price

            # Ajustar por factores (con pesos)
            adjustment = (
                (factors.seasonality * Decimal("0.2") +
                factors.demand * Decimal("0.2") +
                factors.competition * Decimal("0.2") +
                factors.quality * Decimal("0.2") +
                factors.flexibility * Decimal("0.2"))
            )

            # Limitar el ajuste total
            if adjustment > Decimal("1.2"):
                adjustment = Decimal("1.2")
            elif adjustment < Decimal("0.8"):
                adjustment = Decimal("0.8")

            optimal_price *= adjustment

            # Calcular métricas
            margin = (optimal_price - factors.base_cost) / optimal_price
            roi = (optimal_price - factors.base_cost) / factors.base_cost

            return OptimizationResult(
                optimal_price=optimal_price,
                margin=margin,
                roi=roi,
                strategy=strategy,
                metadata={
                    "factors": {k: str(v) for k, v in factors.__dict__.items()},
                    "package_id": str(package.id),
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error optimizando precio: {str(e)}")
            raise

    async def optimize_prices_batch(
        self,
        packages: List[TravelPackage]
    ) -> List[OptimizationResult]:
        """
        Optimiza precios para múltiples paquetes.
        
        Args:
            packages: Lista de paquetes a optimizar
            
        Returns:
            Lista de resultados de optimización
        """
        results = []
        for package in packages:
            try:
                result = await self.optimize_price(package)
                results.append(result)
            except Exception as e:
                logger.error(f"Error optimizando paquete {package.id}: {str(e)}")
                continue
        return results

    async def _extract_price_factors(self, package: TravelPackage) -> PriceFactors:
        """
        Extrae factores que influyen en el precio.
        
        Args:
            package: Paquete a analizar
            
        Returns:
            Factores de precio
        """
        try:
            # Calcular costo base
            base_cost = await self._calculate_base_cost(package)

            # Calcular factores
            seasonality = await self._calculate_seasonality(package)
            demand = await self._calculate_demand(package)
            competition = await self._calculate_competition(package)
            quality = await self._calculate_quality(package)
            flexibility = await self._calculate_flexibility(package)

            return PriceFactors(
                base_cost=base_cost,
                margin=self.default_margin,
                seasonality=seasonality,
                demand=demand,
                competition=competition,
                quality=quality,
                flexibility=flexibility
            )

        except Exception as e:
            logger.error(f"Error extrayendo factores: {str(e)}")
            raise

    async def _calculate_base_cost(self, package: TravelPackage) -> Decimal:
        """Calcula el costo base del paquete."""
        return package.total_price * Decimal("0.7")  # 70% del precio total como costo base

    async def _calculate_seasonality(self, package: TravelPackage) -> Decimal:
        """Calcula el factor de estacionalidad."""
        # Temporada alta: Diciembre-Febrero (verano) y Julio (vacaciones)
        month = package.start_date.month
        if month in [12, 1, 2]:  # Verano
            return Decimal("1.1")
        elif month == 7:  # Vacaciones de invierno
            return Decimal("1.05")
        return Decimal("1.0")

    async def _calculate_demand(self, package: TravelPackage) -> Decimal:
        """Calcula el factor de demanda."""
        # Simplificado: mayor demanda para viajes cortos
        if package.nights <= 3:
            return Decimal("1.1")
        elif package.nights <= 7:
            return Decimal("1.05")
        return Decimal("1.0")

    async def _calculate_competition(self, package: TravelPackage) -> Decimal:
        """Calcula el factor de competencia."""
        # Simplificado: destinos populares tienen más competencia
        popular_destinations = {"Buenos Aires", "Rio de Janeiro", "Santiago"}
        if package.destination in popular_destinations:
            return Decimal("0.95")  # Más competencia = menor precio
        return Decimal("1.0")

    async def _calculate_quality(self, package: TravelPackage) -> Decimal:
        """Calcula el factor de calidad."""
        # Simplificado: mejor calidad para paquetes con más servicios
        services = 0
        if package.flights:
            services += 1
        if package.accommodation:
            services += 1
        if package.activities:
            services += len(package.activities)

        if services >= 4:
            return Decimal("1.1")
        elif services >= 2:
            return Decimal("1.05")
        return Decimal("1.0")

    async def _calculate_flexibility(self, package: TravelPackage) -> Decimal:
        """Calcula el factor de flexibilidad."""
        # Simplificado: más flexibilidad = precio más alto
        flexibility_score = 0
        if package.is_refundable:
            flexibility_score += 1
        if package.modification_policy:
            flexibility_score += 1
        if package.payment_options and len(package.payment_options) > 1:
            flexibility_score += 1

        if flexibility_score >= 2:
            return Decimal("1.1")
        elif flexibility_score >= 1:
            return Decimal("1.05")
        return Decimal("1.0")

    async def _select_strategy(self, package: TravelPackage) -> PricingStrategy:
        """Selecciona la estrategia de precios más adecuada."""
        # Por defecto usar estrategia competitiva
        return PricingStrategy(
            type="competitive",
            params={"margin": self.default_margin}
        )


# Instancia global
price_optimizer = PriceOptimizer()


def get_price_optimizer() -> PriceOptimizer:
    """Obtener instancia del optimizador."""
    return price_optimizer
