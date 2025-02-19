"""Módulo de métricas."""

from typing import Dict, Any, Optional, List
from prometheus_client import Counter, Histogram, CollectorRegistry

class MetricsCollector:
    """Colector de métricas."""

    def __init__(self, module_name: str):
        """Inicializar colector.
        
        Args:
            module_name: Nombre del módulo para el que se recolectan métricas
        """
        self.module_name = module_name
        self.registry = CollectorRegistry()
        
        # Métricas de operaciones
        self.operation_counter = Counter(
            f'{module_name}_operations_total',
            'Number of operations',
            ['operation_name', 'operation_type', 'strategy_type', 'request_type'],
            registry=self.registry
        )
        
        # Métricas de tiempo
        self.operation_time = Histogram(
            f'{module_name}_operation_time_seconds',
            'Time spent on operations',
            ['metric_name', 'operation_type'],
            registry=self.registry
        )
        
        # Métricas de errores
        self.error_counter = Counter(
            f'{module_name}_errors_total',
            'Number of errors',
            ['error_type'],
            registry=self.registry
        )

    def record_operation(self, operation_name: str, **labels):
        """Registrar operación.
        
        Args:
            operation_name: Nombre de la operación
            **labels: Labels adicionales para la métrica
        """
        # Asegurarse que todas las etiquetas estén presentes
        all_labels = {
            'operation_name': operation_name,
            'operation_type': labels.get('operation_type', ''),
            'strategy_type': labels.get('strategy_type', ''),
            'request_type': labels.get('request_type', '')
        }
        self.operation_counter.labels(**all_labels).inc()

    def record_time(self, metric_name: str, value: float, **labels):
        """Registrar tiempo.
        
        Args:
            metric_name: Nombre de la métrica
            value: Valor en segundos
            **labels: Labels adicionales para la métrica
        """
        all_labels = {
            'metric_name': metric_name,
            'operation_type': labels.get('operation_type', '')
        }
        self.operation_time.labels(**all_labels).observe(value)

    def record_error(self, error_type: str):
        """Registrar error.
        
        Args:
            error_type: Tipo de error
        """
        self.error_counter.labels(
            error_type=error_type
        ).inc()

    def increment(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Método de compatibilidad para incrementar contadores.
        
        Args:
            name: Nombre del contador
            value: Valor a incrementar
            labels: Labels para la métrica
        """
        self.record_operation(name, **labels if labels else {})

# Almacén de colectores por módulo
_collectors: Dict[str, MetricsCollector] = {}

def get_metrics_collector(module_name: str) -> MetricsCollector:
    """Obtener instancia del colector para un módulo específico.
    
    Args:
        module_name: Nombre del módulo para el que se requiere el colector
        
    Returns:
        Instancia del colector de métricas para el módulo
    """
    if module_name not in _collectors:
        _collectors[module_name] = MetricsCollector(module_name)
    return _collectors[module_name]
