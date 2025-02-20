"""Monitoring utilities."""

import logging
from typing import Dict, Any
from datetime import datetime


class SimpleMonitor:
    """Monitor simple para el sistema."""

    def __init__(self):
        """Inicializar monitor."""
        self.logger = logging.getLogger(__name__)
        self.metrics = {
            "requests": 0,
            "errors": 0,
            "response_time": 0.0,
            "active_sessions": 0,
        }
        self.start_time = datetime.now()

    def increment(self, metric: str, value: int = 1):
        """Incrementar métrica."""
        if metric in self.metrics:
            self.metrics[metric] += value

    def set(self, metric: str, value: Any):
        """Establecer valor de métrica."""
        self.metrics[metric] = value

    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas actuales."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        return {**self.metrics, "uptime": uptime}

    def error(self, message: str):
        """Registrar error."""
        self.logger.error(message)
        self.increment("errors")

    def info(self, message: str):
        """Registrar información."""
        self.logger.info(message)

    def warning(self, message: str):
        """Registrar advertencia."""
        self.logger.warning(message)


# Instancia global del monitor
monitor = SimpleMonitor()
