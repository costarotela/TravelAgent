"""Módulo para calibración avanzada de confianza."""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime


@dataclass
class CalibrationMetrics:
    """Métricas de calibración de confianza."""

    calibration_score: float
    reliability_score: float
    sharpness_score: float
    resolution_score: float
    uncertainty: float


@dataclass
class ConfidenceBin:
    """Bin para análisis de calibración."""

    predicted_confidence: float
    actual_outcomes: List[float]
    sample_size: int
    empirical_confidence: float


class ConfidenceCalibrator:
    """Sistema avanzado de calibración de confianza."""

    def __init__(self, num_bins: int = 10):
        self.num_bins = num_bins
        self._calibration_map = {}
        self._history = []

    async def calibrate_confidence(
        self,
        predicted_confidence: float,
        action_type: str,
        market_conditions: Dict,
        historical_data: Optional[List] = None,
    ) -> Tuple[float, CalibrationMetrics]:
        """Calibra el nivel de confianza predicho."""
        # Analizar datos históricos
        calibration_bins = self._analyze_historical_data(action_type, historical_data)

        # Calcular métricas de calibración
        metrics = self._calculate_calibration_metrics(calibration_bins)

        # Ajustar confianza
        calibrated_confidence = self._adjust_confidence(
            predicted_confidence, calibration_bins, metrics, market_conditions
        )

        return calibrated_confidence, metrics

    def _analyze_historical_data(
        self, action_type: str, historical_data: Optional[List]
    ) -> List[ConfidenceBin]:
        """Analiza datos históricos para crear bins de calibración."""
        if historical_data is None:
            historical_data = []

        # Filtrar por tipo de acción
        relevant_data = [
            action for action in historical_data if action["type"] == action_type
        ]

        if not relevant_data:
            return []

        # Crear bins
        bins = []
        bin_edges = np.linspace(0, 1, self.num_bins + 1)

        for i in range(self.num_bins):
            lower = bin_edges[i]
            upper = bin_edges[i + 1]
            mid = (lower + upper) / 2

            # Filtrar acciones en este bin
            bin_actions = [
                action
                for action in relevant_data
                if lower <= action.get("confidence", 0) < upper
            ]

            if bin_actions:
                actual_outcomes = [
                    float(action.get("success", False)) for action in bin_actions
                ]

                empirical_conf = np.mean(actual_outcomes)

                bins.append(
                    ConfidenceBin(
                        predicted_confidence=mid,
                        actual_outcomes=actual_outcomes,
                        sample_size=len(bin_actions),
                        empirical_confidence=empirical_conf,
                    )
                )

        return bins

    def _calculate_calibration_metrics(
        self, calibration_bins: List[ConfidenceBin]
    ) -> CalibrationMetrics:
        """Calcula métricas detalladas de calibración."""
        if not calibration_bins:
            return CalibrationMetrics(
                calibration_score=0.0,
                reliability_score=0.0,
                sharpness_score=0.0,
                resolution_score=0.0,
                uncertainty=1.0,
            )

        # Calcular score de calibración
        calibration_errors = [
            abs(bin.predicted_confidence - bin.empirical_confidence)
            for bin in calibration_bins
        ]
        calibration_score = 1.0 - np.mean(calibration_errors)

        # Calcular confiabilidad
        weighted_errors = [
            error * (bin.sample_size / sum(b.sample_size for b in calibration_bins))
            for error, bin in zip(calibration_errors, calibration_bins)
        ]
        reliability_score = 1.0 - np.mean(weighted_errors)

        # Calcular sharpness (qué tan decisivo es el modelo)
        predictions = [bin.predicted_confidence for bin in calibration_bins]
        sharpness_score = np.std(predictions) if len(predictions) > 1 else 0.0

        # Calcular resolución (capacidad de discriminar)
        empirical_confs = [bin.empirical_confidence for bin in calibration_bins]
        resolution_score = np.std(empirical_confs) if len(empirical_confs) > 1 else 0.0

        # Calcular incertidumbre
        total_samples = sum(bin.sample_size for bin in calibration_bins)
        uncertainty = 1.0 / (1.0 + np.log1p(total_samples))

        return CalibrationMetrics(
            calibration_score=calibration_score,
            reliability_score=reliability_score,
            sharpness_score=sharpness_score,
            resolution_score=resolution_score,
            uncertainty=uncertainty,
        )

    def _adjust_confidence(
        self,
        predicted_confidence: float,
        calibration_bins: List[ConfidenceBin],
        metrics: CalibrationMetrics,
        market_conditions: Dict,
    ) -> float:
        """Ajusta el nivel de confianza basado en calibración histórica."""
        if not calibration_bins:
            return predicted_confidence

        # Encontrar el bin más cercano
        closest_bin = min(
            calibration_bins,
            key=lambda x: abs(x.predicted_confidence - predicted_confidence),
        )

        # Calcular factor de ajuste base
        base_adjustment = (
            closest_bin.empirical_confidence - closest_bin.predicted_confidence
        )

        # Ajustar por métricas de calibración
        calibration_weight = metrics.calibration_score
        reliability_weight = metrics.reliability_score

        # Considerar condiciones de mercado
        market_volatility = market_conditions.get("volatility", 0.0)
        market_confidence = 1.0 - market_volatility

        # Calcular ajuste final
        adjustment = (
            base_adjustment
            * calibration_weight
            * reliability_weight
            * market_confidence
        )

        # Aplicar ajuste con límites
        calibrated = predicted_confidence + adjustment
        return max(0.0, min(1.0, calibrated))

    def update_calibration(
        self, predicted_confidence: float, actual_outcome: float, action_type: str
    ) -> None:
        """Actualiza el mapa de calibración con nuevos datos."""
        self._history.append(
            {
                "predicted": predicted_confidence,
                "actual": actual_outcome,
                "type": action_type,
                "timestamp": datetime.now(),
            }
        )

        # Actualizar mapa de calibración
        bin_index = int(predicted_confidence * self.num_bins)
        bin_key = (action_type, bin_index)

        if bin_key not in self._calibration_map:
            self._calibration_map[bin_key] = {"sum": 0.0, "count": 0}

        self._calibration_map[bin_key]["sum"] += actual_outcome
        self._calibration_map[bin_key]["count"] += 1

    def get_calibration_stats(self) -> Dict:
        """Obtiene estadísticas del sistema de calibración."""
        if not self._history:
            return {}

        predictions = [h["predicted"] for h in self._history]
        actuals = [h["actual"] for h in self._history]

        return {
            "mean_predicted": np.mean(predictions),
            "mean_actual": np.mean(actuals),
            "correlation": np.corrcoef(predictions, actuals)[0, 1],
            "num_samples": len(self._history),
            "calibration_map": self._calibration_map,
        }
