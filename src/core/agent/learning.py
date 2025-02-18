"""Sistema de aprendizaje del agente."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np
from collections import defaultdict
import logging

from src.core.database.base import db
from src.core.models.travel import TravelPackage, MarketAnalysis
from src.core.agent.execution import ExecutionResult, TaskExecution
from src.core.cache.redis_cache import cache


@dataclass
class LearningMetrics:
    """Métricas de aprendizaje."""

    accuracy: float
    impact_error: float
    confidence_calibration: float
    execution_success_rate: float
    avg_execution_time: float
    improvement_rate: float


@dataclass
class ActionPerformance:
    """Rendimiento de una acción específica."""

    action_type: str
    success_rate: float
    avg_impact: float
    avg_execution_time: float
    confidence_correlation: float
    risk_assessment_accuracy: float


class LearningSystem:
    """Sistema de aprendizaje y mejora continua."""

    def __init__(self):
        self._performance_history: Dict[str, List[ActionPerformance]] = defaultdict(
            list
        )
        self._route_patterns: Dict[str, Dict] = {}
        self._confidence_adjustments: Dict[str, float] = defaultdict(float)
        self._logger = logging.getLogger(__name__)

    async def learn_from_execution(
        self, route: Tuple[str, str], executions: List[TaskExecution]
    ) -> LearningMetrics:
        """Aprender de una ejecución específica."""
        route_key = f"{route[0]}-{route[1]}"

        # 1. Analizar rendimiento de acciones
        action_performances = []
        for execution in executions:
            performance = await self._analyze_action_performance(execution)
            action_performances.append(performance)

            # Actualizar historial
            self._performance_history[execution.action.type.value].append(performance)

        # 2. Identificar patrones
        await self._update_route_patterns(route, executions)

        # 3. Ajustar factores de confianza
        self._adjust_confidence_factors(route_key, action_performances)

        # 4. Calcular métricas de aprendizaje
        metrics = self._calculate_learning_metrics(executions, action_performances)

        # 5. Almacenar insights
        await self._store_learning_insights(route, metrics, action_performances)

        return metrics

    async def get_route_recommendations(
        self, origin: str, destination: str
    ) -> Dict[str, Any]:
        """Obtener recomendaciones basadas en aprendizaje."""
        route_key = f"{origin}-{destination}"

        # Intentar obtener del caché
        cache_key = f"learning_recommendations:{route_key}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        # Analizar patrones históricos
        patterns = self._route_patterns.get(route_key, {})

        # Obtener rendimiento de acciones
        action_stats = self._get_action_statistics(route_key)

        # Generar recomendaciones
        recommendations = {
            "best_actions": self._get_best_performing_actions(route_key),
            "confidence_adjustments": self._confidence_adjustments[route_key],
            "risk_patterns": patterns.get("risk_patterns", {}),
            "success_factors": patterns.get("success_factors", []),
            "improvement_opportunities": self._identify_improvements(route_key),
        }

        # Guardar en caché
        await cache.set(cache_key, recommendations, ttl=3600)

        return recommendations

    async def _analyze_action_performance(
        self, execution: TaskExecution
    ) -> ActionPerformance:
        """Analizar rendimiento de una acción específica."""
        # Calcular métricas base
        success = execution.result == ExecutionResult.SUCCESS
        impact = execution.impact if execution.impact is not None else 0.0
        execution_time = (execution.end_time - execution.start_time).total_seconds()

        # Obtener historial de acciones similares
        similar_actions = self._performance_history[execution.action.type.value]

        # Calcular estadísticas
        if similar_actions:
            prev_success_rates = [a.success_rate for a in similar_actions]
            prev_impacts = [a.avg_impact for a in similar_actions]
            success_rate = (sum(prev_success_rates) + float(success)) / (
                len(prev_success_rates) + 1
            )
            avg_impact = (sum(prev_impacts) + impact) / (len(prev_impacts) + 1)
        else:
            success_rate = float(success)
            avg_impact = impact

        # Calcular correlación con confianza
        confidence = execution.metadata.get("confidence", 0.0)
        if similar_actions and len(similar_actions) > 1:
            confidences = [a.confidence_correlation for a in similar_actions]
            confidence_correlation = np.mean([confidence] + confidences)
        else:
            confidence_correlation = confidence

        # Evaluar precisión de evaluación de riesgo
        risk_level = execution.metadata.get("risk_level", "low")
        expected_impact = execution.action.expected_impact
        actual_impact = execution.impact if execution.impact is not None else 0.0
        risk_accuracy = 1.0 - min(
            1.0,
            (
                abs(expected_impact - actual_impact) / expected_impact
                if expected_impact > 0
                else 0.0
            ),
        )

        return ActionPerformance(
            action_type=execution.action.type.value,
            success_rate=success_rate,
            avg_impact=avg_impact,
            avg_execution_time=execution_time,
            confidence_correlation=confidence_correlation,
            risk_assessment_accuracy=risk_accuracy,
        )

    async def _update_route_patterns(
        self, route: Tuple[str, str], executions: List[TaskExecution]
    ):
        """Actualizar patrones identificados para una ruta."""
        route_key = f"{route[0]}-{route[1]}"

        # Inicializar si no existe
        if route_key not in self._route_patterns:
            self._route_patterns[route_key] = {
                "risk_patterns": {},
                "success_factors": [],
                "market_conditions": defaultdict(int),
                "execution_patterns": defaultdict(list),
            }

        patterns = self._route_patterns[route_key]

        for execution in executions:
            # Analizar condiciones de mercado
            market_status = execution.metadata.get("market_status")
            if market_status:
                patterns["market_conditions"][market_status] += 1

            # Analizar patrones de riesgo
            risk_level = execution.metadata.get("risk_level")
            if risk_level:
                if risk_level not in patterns["risk_patterns"]:
                    patterns["risk_patterns"][risk_level] = {
                        "count": 0,
                        "success_rate": 0.0,
                        "avg_impact": 0.0,
                    }

                risk_data = patterns["risk_patterns"][risk_level]
                risk_data["count"] += 1
                risk_data["success_rate"] = (
                    risk_data["success_rate"] * (risk_data["count"] - 1)
                    + float(execution.result == ExecutionResult.SUCCESS)
                ) / risk_data["count"]
                if execution.impact is not None:
                    risk_data["avg_impact"] = (
                        risk_data["avg_impact"] * (risk_data["count"] - 1)
                        + execution.impact
                    ) / risk_data["count"]

            # Identificar factores de éxito
            if execution.result == ExecutionResult.SUCCESS:
                success_factor = {
                    "action_type": execution.action.type.value,
                    "market_status": market_status,
                    "risk_level": risk_level,
                    "impact": execution.impact,
                    "conditions": execution.metadata,
                }
                patterns["success_factors"].append(success_factor)

            # Registrar patrón de ejecución
            execution_pattern = {
                "timestamp": execution.start_time.isoformat(),
                "action_type": execution.action.type.value,
                "result": execution.result.value if execution.result else None,
                "impact": execution.impact,
                "duration": (execution.end_time - execution.start_time).total_seconds(),
            }
            patterns["execution_patterns"][execution.action.type.value].append(
                execution_pattern
            )

    def _adjust_confidence_factors(
        self, route_key: str, performances: List[ActionPerformance]
    ):
        """Ajustar factores de confianza basado en rendimiento."""
        if not performances:
            return

        # Calcular ajuste basado en precisión de evaluación de riesgo
        risk_accuracy = np.mean([p.risk_assessment_accuracy for p in performances])

        # Calcular ajuste basado en correlación de confianza
        confidence_correlation = np.mean(
            [p.confidence_correlation for p in performances]
        )

        # Calcular ajuste basado en tasa de éxito
        success_rate = np.mean([p.success_rate for p in performances])

        # Combinar factores
        adjustment = (risk_accuracy + confidence_correlation + success_rate) / 3

        # Aplicar ajuste suavizado
        current = self._confidence_adjustments[route_key]
        self._confidence_adjustments[route_key] = current * 0.7 + adjustment * 0.3

    def _calculate_learning_metrics(
        self, executions: List[TaskExecution], performances: List[ActionPerformance]
    ) -> LearningMetrics:
        """Calcular métricas de aprendizaje."""
        if not executions or not performances:
            return LearningMetrics(
                accuracy=0.0,
                impact_error=0.0,
                confidence_calibration=0.0,
                execution_success_rate=0.0,
                avg_execution_time=0.0,
                improvement_rate=0.0,
            )

        # Calcular precisión general
        successful = sum(1 for e in executions if e.result == ExecutionResult.SUCCESS)
        accuracy = successful / len(executions)

        # Calcular error de impacto
        impact_errors = []
        for execution in executions:
            if execution.impact is not None and execution.action.expected_impact > 0:
                error = abs(execution.impact - execution.action.expected_impact)
                impact_errors.append(error / execution.action.expected_impact)
        impact_error = np.mean(impact_errors) if impact_errors else 1.0

        # Calcular calibración de confianza
        confidence_calibration = np.mean(
            [p.confidence_correlation for p in performances]
        )

        # Calcular tasa de éxito de ejecución
        execution_success_rate = np.mean([p.success_rate for p in performances])

        # Calcular tiempo promedio de ejecución
        avg_execution_time = np.mean([p.avg_execution_time for p in performances])

        # Calcular tasa de mejora
        if len(performances) > 1:
            initial_success = performances[0].success_rate
            final_success = performances[-1].success_rate
            improvement_rate = (
                (final_success - initial_success) / initial_success
                if initial_success > 0
                else 0.0
            )
        else:
            improvement_rate = 0.0

        return LearningMetrics(
            accuracy=accuracy,
            impact_error=impact_error,
            confidence_calibration=confidence_calibration,
            execution_success_rate=execution_success_rate,
            avg_execution_time=avg_execution_time,
            improvement_rate=improvement_rate,
        )

    async def _store_learning_insights(
        self,
        route: Tuple[str, str],
        metrics: LearningMetrics,
        performances: List[ActionPerformance],
    ):
        """Almacenar insights de aprendizaje."""
        with db.get_session() as session:
            analysis = MarketAnalysis(
                origin=route[0],
                destination=route[1],
                avg_price=0.0,  # No aplica para insights
                min_price=0.0,  # No aplica para insights
                max_price=0.0,  # No aplica para insights
                demand_score=metrics.accuracy,
                trend="learning",
                analysis_date=datetime.utcnow(),
                data={
                    "metrics": {
                        "accuracy": metrics.accuracy,
                        "impact_error": metrics.impact_error,
                        "confidence_calibration": metrics.confidence_calibration,
                        "execution_success_rate": metrics.execution_success_rate,
                        "avg_execution_time": metrics.avg_execution_time,
                        "improvement_rate": metrics.improvement_rate,
                    },
                    "performances": [
                        {
                            "action_type": p.action_type,
                            "success_rate": p.success_rate,
                            "avg_impact": p.avg_impact,
                            "avg_execution_time": p.avg_execution_time,
                            "confidence_correlation": p.confidence_correlation,
                            "risk_assessment_accuracy": p.risk_assessment_accuracy,
                        }
                        for p in performances
                    ],
                },
            )
            session.add(analysis)
            session.commit()

    def _get_action_statistics(self, route_key: str) -> Dict[str, Dict]:
        """Obtener estadísticas de acciones para una ruta."""
        patterns = self._route_patterns.get(route_key, {})
        execution_patterns = patterns.get("execution_patterns", {})

        stats = {}
        for action_type, executions in execution_patterns.items():
            if not executions:
                continue

            # Calcular estadísticas
            impacts = [e["impact"] for e in executions if e["impact"] is not None]
            durations = [e["duration"] for e in executions if e["duration"] is not None]
            success_count = sum(1 for e in executions if e["result"] == "success")

            stats[action_type] = {
                "count": len(executions),
                "success_rate": success_count / len(executions),
                "avg_impact": np.mean(impacts) if impacts else 0.0,
                "avg_duration": np.mean(durations) if durations else 0.0,
                "trend": (
                    "improving"
                    if len(impacts) > 1 and impacts[-1] > impacts[0]
                    else "stable"
                ),
            }

        return stats

    def _get_best_performing_actions(self, route_key: str) -> List[Dict]:
        """Obtener las acciones con mejor rendimiento."""
        stats = self._get_action_statistics(route_key)

        # Ordenar por tasa de éxito e impacto
        sorted_actions = sorted(
            stats.items(),
            key=lambda x: (x[1]["success_rate"], x[1]["avg_impact"]),
            reverse=True,
        )

        return [
            {"action_type": action_type, "stats": action_stats}
            for action_type, action_stats in sorted_actions[:3]  # Top 3
        ]

    def _identify_improvements(self, route_key: str) -> List[Dict]:
        """Identificar oportunidades de mejora."""
        stats = self._get_action_statistics(route_key)
        patterns = self._route_patterns.get(route_key, {})

        improvements = []

        # 1. Acciones con baja tasa de éxito
        for action_type, action_stats in stats.items():
            if action_stats["success_rate"] < 0.7:  # Umbral de 70%
                improvements.append(
                    {
                        "type": "low_success_rate",
                        "action_type": action_type,
                        "current_rate": action_stats["success_rate"],
                        "recommendation": "Revisar y ajustar criterios de ejecución",
                    }
                )

        # 2. Patrones de riesgo problemáticos
        risk_patterns = patterns.get("risk_patterns", {})
        for risk_level, risk_data in risk_patterns.items():
            if risk_data["success_rate"] < 0.6:  # Umbral de 60%
                improvements.append(
                    {
                        "type": "high_risk_failure",
                        "risk_level": risk_level,
                        "success_rate": risk_data["success_rate"],
                        "recommendation": "Mejorar evaluación de riesgo y criterios de ejecución",
                    }
                )

        # 3. Oportunidades de optimización
        for action_type, action_stats in stats.items():
            if action_stats["avg_duration"] > 2.0:  # Más de 2 segundos
                improvements.append(
                    {
                        "type": "long_execution",
                        "action_type": action_type,
                        "avg_duration": action_stats["avg_duration"],
                        "recommendation": "Optimizar tiempo de ejecución",
                    }
                )

        return improvements


# Instancia global
learning_system = LearningSystem()
