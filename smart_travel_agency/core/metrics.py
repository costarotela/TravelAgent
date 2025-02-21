"""Sistema de métricas."""

from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram
import logging


class BaseMetrics:
    """Clase base para métricas."""

    def __init__(self, namespace: str):
        """Inicializa métricas base.
        
        Args:
            namespace: Namespace para las métricas
        """
        self.namespace = namespace
        self.logger = logging.getLogger(namespace)


class BudgetMetrics(BaseMetrics):
    """Métricas específicas para presupuestos."""

    def __init__(self):
        """Inicializa métricas de presupuestos."""
        super().__init__("budget")
        
        # Operaciones de reconstrucción
        self.reconstruction_operations = Counter(
            f"{self.namespace}_reconstruction_operations_total",
            "Number of reconstruction operations",
            ["strategy"]
        )
        
        self.reconstruction_latency = Histogram(
            f"{self.namespace}_reconstruction_latency_seconds",
            "Latency of reconstruction operations",
            ["strategy"]
        )
        
        # Búsqueda de alternativas
        self.alternatives_found = Counter(
            f"{self.namespace}_alternatives_found_total",
            "Number of alternatives found",
            ["item_type", "reason"]
        )
        
        self.alternative_scores = Histogram(
            f"{self.namespace}_alternative_scores",
            "Distribution of alternative scores",
            ["item_type", "factor"]
        )
    
    def record_reconstruction(
        self,
        strategy: str,
        duration: Optional[float] = None
    ) -> None:
        """Registra una operación de reconstrucción."""
        self.reconstruction_operations.labels(
            strategy=strategy
        ).inc()
        
        if duration is not None:
            self.reconstruction_latency.labels(
                strategy=strategy
            ).observe(duration)
            
        self.logger.debug(
            f"Reconstruction operation recorded: strategy={strategy}, duration={duration}"
        )
    
    def record_alternative_found(
        self,
        item_type: str,
        reason: str
    ) -> None:
        """Registra una alternativa encontrada."""
        self.alternatives_found.labels(
            item_type=item_type,
            reason=reason
        ).inc()
        
        self.logger.debug(
            f"Alternative found: type={item_type}, reason={reason}"
        )
    
    def record_alternative_score(
        self,
        item_type: str,
        factor: str,
        score: float
    ) -> None:
        """Registra el score de una alternativa."""
        self.alternative_scores.labels(
            item_type=item_type,
            factor=factor
        ).observe(score)
        
        self.logger.debug(
            f"Alternative score: type={item_type}, factor={factor}, score={score}"
        )


# Instancias globales
_budget_metrics = BudgetMetrics()


def get_budget_metrics() -> BudgetMetrics:
    """Obtiene la instancia global de métricas de presupuestos."""
    return _budget_metrics
