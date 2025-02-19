"""
Protector de estabilidad de sesiones.

Este módulo implementa:
1. Validación de cambios
2. Control de estabilidad
3. Prevención de interrupciones
4. Monitoreo de modificaciones
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from prometheus_client import Counter, Gauge

from ..schemas import (
    SessionState,
    Budget,
    TravelPackage,
    StabilityMetrics,
    ChangeImpact
)
from ..metrics import get_metrics_collector
from .state_manager import get_session_manager

# Métricas
STABILITY_SCORE = Gauge(
    'session_stability_score',
    'Current stability score of session',
    ['session_id']
)

STABILITY_VIOLATIONS = Counter(
    'stability_violations_total',
    'Number of stability violations',
    ['violation_type']
)

class StabilityGuard:
    """
    Protector de estabilidad.
    
    Responsabilidades:
    1. Validar cambios
    2. Mantener estabilidad
    3. Prevenir interrupciones
    """

    def __init__(self):
        """Inicializar protector."""
        self.logger = logging.getLogger(__name__)
        self.metrics = get_metrics_collector()
        
        # Configuración
        self.config = {
            "max_price_change": 0.15,     # 15% máximo cambio de precio
            "max_margin_change": 0.1,      # 10% máximo cambio de margen
            "min_stability_score": 0.7,    # 70% mínimo de estabilidad
            "critical_threshold": 0.5      # 50% umbral crítico
        }
        
        # Métricas de estabilidad por sesión
        self._stability_metrics: Dict[str, StabilityMetrics] = {}

    async def validate_change(
        self,
        session_id: str,
        proposed_budget: Budget
    ) -> ChangeImpact:
        """
        Validar impacto de un cambio propuesto.
        
        Args:
            session_id: ID de la sesión
            proposed_budget: Presupuesto propuesto
            
        Returns:
            Impacto del cambio
        """
        try:
            # Obtener sesión actual
            session_manager = await get_session_manager()
            session = await session_manager.get_session(session_id)
            
            if not session or not session.is_active:
                return ChangeImpact(
                    is_safe=False,
                    stability_score=0.0,
                    violations=["invalid_session"]
                )
            
            # Calcular métricas de estabilidad
            metrics = await self._calculate_metrics(
                session.budget,
                proposed_budget
            )
            
            # Actualizar métricas
            self._stability_metrics[session_id] = metrics
            
            # Registrar métricas
            STABILITY_SCORE.labels(
                session_id=session_id
            ).set(metrics.stability_score)
            
            # Validar violaciones
            violations = await self._check_violations(metrics)
            
            for violation in violations:
                STABILITY_VIOLATIONS.labels(
                    violation_type=violation
                ).inc()
            
            return ChangeImpact(
                is_safe=len(violations) == 0,
                stability_score=metrics.stability_score,
                violations=violations
            )
            
        except Exception as e:
            self.logger.error(f"Error validando cambio: {e}")
            return ChangeImpact(
                is_safe=False,
                stability_score=0.0,
                violations=[str(e)]
            )

    async def get_stability_metrics(
        self,
        session_id: str
    ) -> Optional[StabilityMetrics]:
        """
        Obtener métricas de estabilidad.
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Métricas de estabilidad o None
        """
        try:
            return self._stability_metrics.get(session_id)
            
        except Exception as e:
            self.logger.error(f"Error obteniendo métricas: {e}")
            return None

    async def monitor_session(
        self,
        session_id: str
    ) -> None:
        """
        Monitorear estabilidad de sesión.
        
        Args:
            session_id: ID de la sesión
        """
        try:
            metrics = await self.get_stability_metrics(session_id)
            
            if not metrics:
                return
            
            # Verificar umbral crítico
            if metrics.stability_score < self.config["critical_threshold"]:
                self.logger.warning(
                    f"Estabilidad crítica en sesión {session_id}: "
                    f"{metrics.stability_score:.2f}"
                )
                
                # Notificar al sistema
                await self._notify_critical_stability(
                    session_id,
                    metrics
                )
            
        except Exception as e:
            self.logger.error(f"Error monitoreando sesión: {e}")

    async def _calculate_metrics(
        self,
        current_budget: Budget,
        proposed_budget: Budget
    ) -> StabilityMetrics:
        """Calcular métricas de estabilidad."""
        try:
            metrics = StabilityMetrics(
                price_changes=[],
                margin_changes=[],
                stability_score=1.0
            )
            
            if not current_budget or not proposed_budget:
                return metrics
            
            # Calcular cambios de precio
            for old_pkg, new_pkg in zip(
                current_budget.packages,
                proposed_budget.packages
            ):
                if old_pkg.price > 0:
                    price_change = abs(
                        (new_pkg.price - old_pkg.price) /
                        old_pkg.price
                    )
                    metrics.price_changes.append(price_change)
                
                if old_pkg.price > old_pkg.cost:
                    old_margin = (old_pkg.price - old_pkg.cost) / old_pkg.price
                    new_margin = (new_pkg.price - new_pkg.cost) / new_pkg.price
                    
                    margin_change = abs(new_margin - old_margin)
                    metrics.margin_changes.append(margin_change)
            
            # Calcular score de estabilidad
            if metrics.price_changes:
                price_factor = 1 - (max(metrics.price_changes) / self.config["max_price_change"])
            else:
                price_factor = 1.0
            
            if metrics.margin_changes:
                margin_factor = 1 - (max(metrics.margin_changes) / self.config["max_margin_change"])
            else:
                margin_factor = 1.0
            
            metrics.stability_score = min(price_factor, margin_factor)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculando métricas: {e}")
            return StabilityMetrics(
                price_changes=[],
                margin_changes=[],
                stability_score=0.0
            )

    async def _check_violations(
        self,
        metrics: StabilityMetrics
    ) -> List[str]:
        """Verificar violaciones de estabilidad."""
        try:
            violations = []
            
            # Validar score general
            if metrics.stability_score < self.config["min_stability_score"]:
                violations.append("low_stability_score")
            
            # Validar cambios de precio
            if any(
                change > self.config["max_price_change"]
                for change in metrics.price_changes
            ):
                violations.append("excessive_price_change")
            
            # Validar cambios de margen
            if any(
                change > self.config["max_margin_change"]
                for change in metrics.margin_changes
            ):
                violations.append("excessive_margin_change")
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Error verificando violaciones: {e}")
            return ["validation_error"]

    async def _notify_critical_stability(
        self,
        session_id: str,
        metrics: StabilityMetrics
    ) -> None:
        """Notificar estabilidad crítica."""
        try:
            # TODO: Implementar sistema de notificaciones
            self.logger.warning(
                f"Estabilidad crítica en sesión {session_id}:\n"
                f"Score: {metrics.stability_score:.2f}\n"
                f"Cambios de precio: {max(metrics.price_changes):.2f}\n"
                f"Cambios de margen: {max(metrics.margin_changes):.2f}"
            )
            
        except Exception as e:
            self.logger.error(f"Error notificando estabilidad: {e}")

# Instancia global
stability_guard = StabilityGuard()

async def get_stability_guard() -> StabilityGuard:
    """Obtener instancia del protector."""
    return stability_guard
