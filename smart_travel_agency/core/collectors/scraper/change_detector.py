"""
Sistema avanzado de detección y análisis de cambios.

Este módulo implementa:
1. Detección de cambios en paquetes turísticos
2. Análisis de impacto en presupuestos
3. Priorización de cambios para optimización
4. Registro de decisiones y métricas
"""

from typing import Dict, Optional, List, Any, Tuple
from decimal import Decimal
from datetime import datetime
import json
import logging
from dataclasses import dataclass

from prometheus_client import Counter, Histogram, Gauge

# Métricas para seguimiento
CHANGES_DETECTED = Counter(
    "package_changes_detected_total",
    "Total number of package changes detected",
    ["change_type", "optimization_pass"],
)

CHANGE_MAGNITUDE = Histogram(
    "package_change_magnitude",
    "Magnitude of changes detected in packages",
    ["change_type", "optimization_pass"],
    buckets=[1, 2, 5, 10, 20, 50, 100],
)

OPTIMIZATION_POTENTIAL = Gauge(
    "package_optimization_potential",
    "Estimated potential for further optimization",
    ["package_type"],
)


@dataclass
class ChangeImpact:
    """Análisis de impacto de un cambio."""

    change_type: str
    magnitude: float
    optimization_potential: float
    affected_components: List[str]
    recommendation: str


class ChangeAnalyzer:
    """
    Sistema avanzado de análisis y priorización de cambios.
    """

    def __init__(self, optimization_threshold: float = 5.0):
        self.optimization_threshold = optimization_threshold
        self.logger = logging.getLogger(__name__)

    def analyze_impact(self, change: Dict[str, Any]) -> ChangeImpact:
        """
        Analiza el impacto potencial de un cambio.

        Args:
            change: Diccionario con detalles del cambio

        Returns:
            ChangeImpact con análisis detallado
        """
        impact = 0.0
        affected = []
        potential = 0.0

        if "precio" in change:
            impact = abs(change["precio"]["diferencia_porcentual"])
            affected.append("precio_base")

            # Analizar potencial de optimización
            if change["precio"]["diferencia"] < 0:
                potential = abs(change["precio"]["diferencia_porcentual"])

        if "impuestos" in change:
            tax_impact = abs(change["impuestos"]["diferencia_porcentual"])
            impact = max(impact, tax_impact)
            affected.append("impuestos")

        if "disponibilidad" in change:
            affected.append("disponibilidad")
            # Analizar impacto en fechas
            removed = len(change["disponibilidad"]["fechas_removidas"])
            added = len(change["disponibilidad"]["fechas_agregadas"])
            if removed > added:
                impact = max(
                    impact, 10.0
                )  # Alto impacto si hay pérdida de disponibilidad

        # Determinar recomendación
        recommendation = self._generate_recommendation(impact, potential, affected)

        return ChangeImpact(
            change_type="precio" if "precio" in change else "otro",
            magnitude=impact,
            optimization_potential=potential,
            affected_components=affected,
            recommendation=recommendation,
        )

    def _generate_recommendation(
        self, impact: float, potential: float, affected: List[str]
    ) -> str:
        """Genera una recomendación basada en el análisis."""
        if impact > self.optimization_threshold:
            if potential > 0:
                return "OPTIMIZAR: Alto potencial de mejora en precio"
            elif "disponibilidad" in affected:
                return "URGENTE: Revisar cambios en disponibilidad"
            else:
                return "REVISAR: Cambio significativo detectado"
        else:
            return "MONITOREAR: Cambio menor, continuar seguimiento"


class ChangeDetector:
    """
    Detector avanzado de cambios con soporte para optimización multi-pasada.
    """

    def __init__(self, optimization_threshold: float = 5.0):
        """
        Inicializa el detector con análisis de optimización.

        Args:
            optimization_threshold: Umbral para considerar cambios significativos
        """
        self.analyzer = ChangeAnalyzer(optimization_threshold)
        self.logger = logging.getLogger(__name__)
        self.optimization_threshold = optimization_threshold
        self.current_pass = 0

    def detect_changes(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        pass_number: Optional[int] = None,
    ) -> Tuple[Dict[str, Any], ChangeImpact]:
        """
        Detecta y analiza cambios entre versiones de datos.

        Args:
            old_data: Datos anteriores
            new_data: Datos nuevos
            pass_number: Número de pasada de optimización

        Returns:
            Tuple con los cambios detectados y su análisis de impacto
        """
        self.current_pass = pass_number or self.current_pass + 1
        changes = {}

        # Detectar cambios en precio
        if old_data["precio"] != new_data["precio"]:
            diferencia = Decimal(str(new_data["precio"])) - Decimal(
                str(old_data["precio"])
            )
            diferencia_porcentual = abs(
                diferencia / Decimal(str(old_data["precio"])) * 100
            )

            changes["precio"] = {
                "anterior": str(old_data["precio"]),
                "actual": str(new_data["precio"]),
                "diferencia": str(diferencia),
                "diferencia_porcentual": float(diferencia_porcentual),
            }

            CHANGES_DETECTED.labels(
                change_type="precio", optimization_pass=self.current_pass
            ).inc()

            CHANGE_MAGNITUDE.labels(
                change_type="precio", optimization_pass=self.current_pass
            ).observe(float(diferencia_porcentual))

        # Detectar cambios en disponibilidad
        old_fechas = set(old_data.get("fechas", []))
        new_fechas = set(new_data.get("fechas", []))

        fechas_removidas = old_fechas - new_fechas
        fechas_agregadas = new_fechas - old_fechas

        if fechas_removidas or fechas_agregadas:
            changes["disponibilidad"] = {
                "fechas_removidas": sorted(list(fechas_removidas)),
                "fechas_agregadas": sorted(list(fechas_agregadas)),
            }

            CHANGES_DETECTED.labels(
                change_type="disponibilidad", optimization_pass=self.current_pass
            ).inc()

        # Analizar impacto y potencial de optimización
        impact = self.analyzer.analyze_impact(changes)

        # Actualizar métrica de potencial de optimización
        OPTIMIZATION_POTENTIAL.labels(
            package_type=new_data.get("tipo", "desconocido")
        ).set(impact.optimization_potential)

        return changes, impact

    def should_continue_optimization(self, impact: ChangeImpact) -> bool:
        """
        Determina si se debe continuar con más pasadas de optimización.

        Args:
            impact: Análisis de impacto del último cambio

        Returns:
            True si se recomienda continuar optimizando
        """
        return (
            impact.optimization_potential > self.optimization_threshold
            and "OPTIMIZAR" in impact.recommendation
        )
