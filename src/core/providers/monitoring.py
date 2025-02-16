"""Provider monitoring and metrics system."""
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# Métricas Prometheus
PROVIDER_REQUESTS = Counter(
    'provider_requests_total',
    'Total number of requests made to provider',
    ['provider', 'operation', 'status']
)

PROVIDER_LATENCY = Histogram(
    'provider_request_latency_seconds',
    'Request latency in seconds',
    ['provider', 'operation'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

PROVIDER_CACHE_HITS = Counter(
    'provider_cache_hits_total',
    'Total number of cache hits',
    ['provider', 'cache_type']
)

PROVIDER_ERRORS = Counter(
    'provider_errors_total',
    'Total number of provider errors',
    ['provider', 'error_type']
)

PROVIDER_AVAILABILITY = Gauge(
    'provider_availability',
    'Provider availability status',
    ['provider']
)

@dataclass
class OperationMetrics:
    """Metrics for a single operation."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_latency: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: Dict[str, int] = field(default_factory=dict)
    last_success: Optional[datetime] = None
    last_error: Optional[datetime] = None
    last_error_message: Optional[str] = None

class ProviderMonitor:
    """Monitor system for provider operations."""

    def __init__(self, provider_name: str):
        """Initialize provider monitor."""
        self.provider_name = provider_name
        self.metrics: Dict[str, OperationMetrics] = {}
        self.status = "operational"
        self._last_check = datetime.now()
        PROVIDER_AVAILABILITY.labels(provider=provider_name).set(1)

    def start_operation(self, operation: str) -> float:
        """Start timing an operation."""
        if operation not in self.metrics:
            self.metrics[operation] = OperationMetrics()
        return time.time()

    def end_operation(
        self,
        operation: str,
        start_time: float,
        success: bool = True,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        cached: bool = False
    ) -> None:
        """Record operation completion."""
        duration = time.time() - start_time
        metrics = self.metrics[operation]
        
        # Actualizar métricas básicas
        metrics.total_calls += 1
        metrics.total_latency += duration
        
        if success:
            metrics.successful_calls += 1
            metrics.last_success = datetime.now()
            status = "success"
        else:
            metrics.failed_calls += 1
            metrics.last_error = datetime.now()
            metrics.last_error_message = error_message
            if error_type:
                metrics.errors[error_type] = metrics.errors.get(error_type, 0) + 1
            status = "error"

        if cached:
            metrics.cache_hits += 1
        else:
            metrics.cache_misses += 1

        # Actualizar métricas Prometheus
        PROVIDER_REQUESTS.labels(
            provider=self.provider_name,
            operation=operation,
            status=status
        ).inc()

        PROVIDER_LATENCY.labels(
            provider=self.provider_name,
            operation=operation
        ).observe(duration)

        if cached:
            PROVIDER_CACHE_HITS.labels(
                provider=self.provider_name,
                cache_type=operation
            ).inc()

        if error_type:
            PROVIDER_ERRORS.labels(
                provider=self.provider_name,
                error_type=error_type
            ).inc()

        # Actualizar estado del proveedor
        self._update_provider_status()

    def _update_provider_status(self) -> None:
        """Update provider status based on recent operations."""
        now = datetime.now()
        self._last_check = now
        
        # Verificar errores recientes (últimos 5 minutos)
        recent_errors = sum(
            1 for m in self.metrics.values()
            if m.last_error and now - m.last_error < timedelta(minutes=5)
        )
        
        # Verificar éxitos recientes
        recent_success = any(
            m.last_success and now - m.last_success < timedelta(minutes=5)
            for m in self.metrics.values()
        )

        # Determinar estado
        if recent_errors > 10:
            self.status = "degraded"
            PROVIDER_AVAILABILITY.labels(provider=self.provider_name).set(0.5)
        elif not recent_success:
            self.status = "unavailable"
            PROVIDER_AVAILABILITY.labels(provider=self.provider_name).set(0)
        else:
            self.status = "operational"
            PROVIDER_AVAILABILITY.labels(provider=self.provider_name).set(1)

    def get_metrics(self) -> Dict[str, Dict]:
        """Get current metrics for all operations."""
        return {
            operation: {
                "total_calls": metrics.total_calls,
                "success_rate": (
                    metrics.successful_calls / metrics.total_calls
                    if metrics.total_calls > 0 else 0
                ),
                "average_latency": (
                    metrics.total_latency / metrics.total_calls
                    if metrics.total_calls > 0 else 0
                ),
                "cache_hit_rate": (
                    metrics.cache_hits / (metrics.cache_hits + metrics.cache_misses)
                    if (metrics.cache_hits + metrics.cache_misses) > 0 else 0
                ),
                "recent_errors": [
                    error_type
                    for error_type, count in metrics.errors.items()
                    if count > 0
                ],
                "last_success": metrics.last_success,
                "last_error": metrics.last_error,
                "last_error_message": metrics.last_error_message
            }
            for operation, metrics in self.metrics.items()
        }

    def get_status(self) -> Dict[str, any]:
        """Get current provider status."""
        return {
            "status": self.status,
            "last_check": self._last_check,
            "metrics": self.get_metrics()
        }
