import logging
from typing import Dict, List, Optional
from datetime import datetime
from prometheus_client import Counter, Histogram

from .providers.ola_models import PaqueteOLA

# Métricas
SIGNIFICANT_CHANGES = Counter(
    "significant_changes_total", "Number of significant changes detected"
)
ANALYSIS_DURATION = Histogram(
    "change_analysis_duration_seconds", "Time spent analyzing changes"
)

logger = logging.getLogger(__name__)


class ChangeDetector:
    """
    Detector de cambios que analiza reportes de actualización y desencadena acciones.
    """

    def __init__(
        self,
        update_threshold: int = 5,
        price_change_threshold: float = 0.1,
        availability_threshold: float = 0.2,
    ):
        """
        Inicializa el detector.

        Args:
            update_threshold: Umbral de actualizaciones para análisis adicional
            price_change_threshold: Umbral de cambio de precio (porcentaje)
            availability_threshold: Umbral de cambio en disponibilidad
        """
        self.update_threshold = update_threshold
        self.price_change_threshold = price_change_threshold
        self.availability_threshold = availability_threshold

    def analyze_report(self, report: Dict[str, List[PaqueteOLA]]) -> Dict[str, any]:
        """
        Analiza el reporte de cambios.

        Args:
            report: Reporte de cambios del actualizador

        Returns:
            Diccionario con resultados del análisis
        """
        start_time = datetime.now()

        try:
            # Estadísticas básicas
            stats = {
                "total_nuevos": len(report.get("nuevos", [])),
                "total_actualizados": len(report.get("actualizados", [])),
                "total_eliminados": len(report.get("eliminados", [])),
                "cambios_significativos": False,
                "acciones_requeridas": [],
            }

            # Analizar cambios significativos
            if self._detect_significant_changes(report, stats):
                stats["cambios_significativos"] = True
                SIGNIFICANT_CHANGES.inc()
                self._trigger_additional_analysis(report, stats)

            # Registrar duración
            duration = (datetime.now() - start_time).total_seconds()
            ANALYSIS_DURATION.observe(duration)

            logger.info(
                f"Análisis completado en {duration:.2f}s - "
                f"Nuevos: {stats['total_nuevos']}, "
                f"Actualizados: {stats['total_actualizados']}, "
                f"Eliminados: {stats['total_eliminados']}"
            )

            return stats

        except Exception as e:
            logger.error(f"Error en analyze_report: {str(e)}")
            raise

    def _detect_significant_changes(
        self, report: Dict[str, List[PaqueteOLA]], stats: Dict[str, any]
    ) -> bool:
        """
        Detecta si hay cambios significativos.

        Args:
            report: Reporte de cambios
            stats: Estadísticas actuales

        Returns:
            True si hay cambios significativos
        """
        # Verificar umbral de actualizaciones
        if stats["total_actualizados"] > self.update_threshold:
            logger.info(f"Detectadas {stats['total_actualizados']} actualizaciones")
            return True

        # Analizar cambios de precio
        if report.get("actualizados"):
            price_changes = []
            for pkg in report["actualizados"]:
                if hasattr(pkg, "precio_anterior"):
                    change_pct = abs(
                        float(pkg.precio) - float(pkg.precio_anterior)
                    ) / float(pkg.precio_anterior)

                    if change_pct > self.price_change_threshold:
                        price_changes.append(
                            {
                                "id": pkg.id,
                                "destino": pkg.destino,
                                "cambio_porcentual": change_pct,
                            }
                        )

            if price_changes:
                logger.info(
                    f"Detectados {len(price_changes)} cambios "
                    f"significativos de precio"
                )
                stats["cambios_precio"] = price_changes
                return True

        return False

    def _trigger_additional_analysis(
        self, report: Dict[str, List[PaqueteOLA]], stats: Dict[str, any]
    ) -> None:
        """
        Desencadena análisis adicional.

        Args:
            report: Reporte de cambios
            stats: Estadísticas actuales
        """
        acciones = []

        # Analizar tendencias de precio
        if stats.get("cambios_precio"):
            acciones.append(
                {
                    "tipo": "analisis_precios",
                    "detalles": "Analizar tendencias de cambios de precio",
                }
            )

        # Verificar disponibilidad
        if report.get("actualizados"):
            disponibilidad_reducida = []
            for pkg in report["actualizados"]:
                if hasattr(pkg, "disponibilidad_anterior"):
                    change = (
                        pkg.disponibilidad - pkg.disponibilidad_anterior
                    ) / pkg.disponibilidad_anterior

                    if change < -self.availability_threshold:
                        disponibilidad_reducida.append(
                            {"id": pkg.id, "destino": pkg.destino, "cambio": change}
                        )

            if disponibilidad_reducida:
                acciones.append(
                    {
                        "tipo": "alerta_disponibilidad",
                        "detalles": disponibilidad_reducida,
                    }
                )

        stats["acciones_requeridas"] = acciones

        logger.info(
            f"Análisis adicional completado - " f"{len(acciones)} acciones requeridas"
        )
