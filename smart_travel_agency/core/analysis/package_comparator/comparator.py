"""
Comparador de paquetes turísticos.

Este módulo implementa:
1. Comparación de paquetes turísticos
2. Cálculo de similitud entre paquetes
3. Recomendación de alternativas
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
import logging
import time
from datetime import datetime

from smart_travel_agency.core.schemas import (
    TravelPackage,
    ComparisonResult,
    CompetitivePosition,
)
from smart_travel_agency.core.metrics import get_budget_metrics


class PackageComparator:
    """Comparador de paquetes turísticos."""

    def __init__(self):
        """Inicializar comparador."""
        self.logger = logging.getLogger(__name__)
        self.metrics = get_budget_metrics()

        # Configuración
        self.config = {
            "similarity_threshold": 0.8,  # Umbral de similitud
            "price_weight": 0.4,  # Peso del precio en comparación
            "features_weight": 0.6,  # Peso de características
            "max_alternatives": 5,  # Máximo de alternativas
        }

    async def compare_packages(
        self,
        package_a: TravelPackage,
        package_b: TravelPackage,
    ) -> ComparisonResult:
        """
        Comparar dos paquetes turísticos.

        Args:
            package_a: Primer paquete
            package_b: Segundo paquete

        Returns:
            Resultado de la comparación
        """
        try:
            start_time = time.time()

            # Calcular similitud
            similarity = self._calculate_similarity(package_a, package_b)

            # Comparar precios
            price_diff = self._compare_prices(package_a, package_b)

            # Comparar características
            features_comparison = self._compare_features(package_a, package_b)

            # Registrar métricas
            duration = time.time() - start_time
            self.metrics.record_reconstruction(
                strategy="package_comparison",
                duration=duration
            )

            # Crear posición competitiva
            position = CompetitivePosition(
                price_percentile=float(similarity),
                quality_percentile=float(similarity),
                flexibility_percentile=float(similarity),
                position="standard" if similarity > 0.5 else "budget"
            )

            return ComparisonResult(
                target_id=package_a.package_id,
                position=position,
                opportunities=[],
                metadata={
                    "similarity": similarity,
                    "price_difference": str(price_diff),
                    "features": features_comparison,
                    "execution_time": duration
                }
            )

        except Exception as e:
            self.logger.error(f"Error en comparación: {str(e)}")
            raise

    def _calculate_similarity(
        self,
        package_a: TravelPackage,
        package_b: TravelPackage
    ) -> float:
        """Calcular similitud entre paquetes."""
        try:
            # Calcular similitud base
            similarity = 0.0

            # Comparar categorías
            if package_a.description == package_b.description:
                similarity += 0.3

            # Comparar precios (diferencia normalizada)
            price_diff = abs(package_a.margin - package_b.margin)
            price_similarity = 1 - min(price_diff, 1.0)
            similarity += 0.4 * price_similarity

            # Comparar políticas
            policy_similarity = 0.0
            if package_a.cancellation_policy == package_b.cancellation_policy:
                policy_similarity += 0.5
            if package_a.modification_policy == package_b.modification_policy:
                policy_similarity += 0.5
            similarity += 0.3 * policy_similarity

            # Registrar score
            self.metrics.record_alternative_score(
                item_type="package",
                factor="similarity",
                score=similarity
            )

            return similarity

        except Exception as e:
            self.logger.error(f"Error calculando similitud: {str(e)}")
            raise

    def _compare_prices(
        self,
        package_a: TravelPackage,
        package_b: TravelPackage
    ) -> Decimal:
        """Comparar precios entre paquetes."""
        try:
            # Obtener precios totales
            total_a = Decimal("0")
            total_b = Decimal("0")

            # Sumar vuelos
            if package_a.flights:
                total_a += sum(f.price for f in package_a.flights)
            if package_b.flights:
                total_b += sum(f.price for f in package_b.flights)

            # Sumar alojamientos
            if package_a.accommodations:
                total_a += sum(a.price for a in package_a.accommodations)
            if package_b.accommodations:
                total_b += sum(a.price for a in package_b.accommodations)

            # Sumar actividades
            if package_a.activities:
                total_a += sum(a.price for a in package_a.activities)
            if package_b.activities:
                total_b += sum(a.price for a in package_b.activities)

            price_diff = total_b - total_a
            
            # Registrar diferencia
            self.metrics.record_alternative_score(
                item_type="package",
                factor="price_difference",
                score=float(price_diff)
            )

            return price_diff

        except Exception as e:
            self.logger.error(f"Error comparando precios: {str(e)}")
            raise

    def _compare_features(
        self,
        package_a: TravelPackage,
        package_b: TravelPackage
    ) -> Dict[str, Any]:
        """Comparar características entre paquetes."""
        try:
            features = {}

            # Comparar políticas
            features["policies"] = {
                "cancellation": {
                    "match": package_a.cancellation_policy == package_b.cancellation_policy,
                    "a": package_a.cancellation_policy,
                    "b": package_b.cancellation_policy
                },
                "modification": {
                    "match": package_a.modification_policy == package_b.modification_policy,
                    "a": package_a.modification_policy,
                    "b": package_b.modification_policy
                }
            }

            # Comparar opciones de pago
            features["payment_options"] = {
                "a": package_a.payment_options or [],
                "b": package_b.payment_options or [],
                "common": list(
                    set(package_a.payment_options or []) & 
                    set(package_b.payment_options or [])
                )
            }

            # Registrar hallazgos
            if features["policies"]["cancellation"]["match"]:
                self.metrics.record_alternative_found(
                    item_type="package",
                    reason="policy_match"
                )

            return features

        except Exception as e:
            self.logger.error(f"Error comparando características: {str(e)}")
            raise


# Instancia global
package_comparator = PackageComparator()


def get_package_comparator() -> PackageComparator:
    """Obtener instancia del comparador de paquetes.

    Returns:
        Instancia del comparador de paquetes
    """
    return PackageComparator()
