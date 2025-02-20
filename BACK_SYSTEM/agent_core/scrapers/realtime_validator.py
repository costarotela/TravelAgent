"""
Validador en tiempo real de cambios en paquetes turísticos.

Este módulo implementa la validación en tiempo real de cambios,
con énfasis en cambios de precios y disponibilidad.
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime
import asyncio
from prometheus_client import Counter, Histogram, Gauge

from .change_detector import ChangeDetector
from .validators import DataValidator, ValidationError
from .error_handler import ErrorHandler
from ..interfaces import EventEmitter, MetricsCollector, Logger, AgentComponent

# Métricas Prometheus
PRICE_CHANGES = Counter(
    "realtime_price_changes_total",
    "Total number of price changes detected in realtime",
    ["change_type", "magnitude_range"],
)

PRICE_CHANGE_MAGNITUDE = Histogram(
    "realtime_price_change_magnitude",
    "Magnitude of price changes in realtime",
    ["change_type"],
    buckets=[1, 2, 5, 10, 15, 20, 30, 50],
)

AVAILABILITY_CHANGES = Counter(
    "realtime_availability_changes_total",
    "Total number of availability changes detected in realtime",
    ["change_type"],
)

VALIDATION_LATENCY = Histogram(
    "realtime_validation_latency_seconds",
    "Time taken to validate changes in realtime",
    ["validation_type"],
    buckets=[0.1, 0.5, 1, 2, 5],
)

ACTIVE_VALIDATIONS = Gauge(
    "realtime_active_validations", "Number of validations currently in progress"
)


class RealtimeValidator(AgentComponent):
    """
    Validador en tiempo real de cambios en paquetes turísticos.

    Attributes:
        change_detector: Detector de cambios
        validator: Validador de datos
        error_handler: Manejador de errores
        notification_queue: Cola de notificaciones
    """

    def __init__(self, logger: Logger, metrics: MetricsCollector, events: EventEmitter):
        """Inicializa el validador en tiempo real."""
        super().__init__(logger, metrics, events)
        self.change_detector = ChangeDetector()
        self.validator = DataValidator()
        self.error_handler = ErrorHandler("realtime_validator")
        self.notification_queue = asyncio.Queue()
        self.price_alert_threshold = 10  # Porcentaje
        self.availability_check_interval = 300  # 5 minutos

    async def validate_price_change(
        self, package_id: str, old_price: Decimal, new_price: Decimal
    ) -> Dict[str, Any]:
        """
        Valida un cambio de precio en tiempo real.

        Args:
            package_id: ID del paquete
            old_price: Precio anterior
            new_price: Precio nuevo

        Returns:
            Dict con resultado de validación
        """
        start_time = datetime.now()
        ACTIVE_VALIDATIONS.inc()

        try:
            if new_price <= 0:
                raise ValidationError("Precio nuevo inválido")

            change_pct = abs((new_price - old_price) / old_price * 100)

            # Registrar métricas
            PRICE_CHANGES.labels(
                change_type="increase" if new_price > old_price else "decrease",
                magnitude_range=f"{int(change_pct/10)*10}-{int(change_pct/10)*10+10}",
            ).inc()

            PRICE_CHANGE_MAGNITUDE.labels(change_type="price").observe(change_pct)

            # Generar resultado
            result = {
                "valid": True,
                "change_percentage": change_pct,
                "requires_alert": change_pct >= self.price_alert_threshold,
                "timestamp": datetime.now().isoformat(),
            }

            # Emitir evento si el cambio es significativo
            if result["requires_alert"]:
                await self.emit_event(
                    "significant_price_change",
                    {
                        "package_id": package_id,
                        "old_price": str(old_price),
                        "new_price": str(new_price),
                        "change_percentage": change_pct,
                    },
                )

            return result

        except Exception as e:
            self.error_handler.log_error(
                "price_validation_error",
                {
                    "error": str(e),
                    "package_id": package_id,
                    "old_price": str(old_price),
                    "new_price": str(new_price),
                },
            )
            raise

        finally:
            ACTIVE_VALIDATIONS.dec()
            VALIDATION_LATENCY.labels(validation_type="price").observe(
                (datetime.now() - start_time).total_seconds()
            )

    async def validate_availability_change(
        self, package_id: str, old_dates: List[str], new_dates: List[str]
    ) -> Dict[str, Any]:
        """
        Valida cambios en disponibilidad en tiempo real.

        Args:
            package_id: ID del paquete
            old_dates: Fechas anteriores
            new_dates: Fechas nuevas

        Returns:
            Dict con resultado de validación
        """
        start_time = datetime.now()
        ACTIVE_VALIDATIONS.inc()

        try:
            # Convertir fechas a set para comparación
            old_set = set(old_dates)
            new_set = set(new_dates)

            # Detectar cambios
            dates_added = list(new_set - old_set)
            dates_removed = list(old_set - new_set)

            # Registrar métricas
            if dates_added:
                AVAILABILITY_CHANGES.labels(change_type="dates_added").inc()

            if dates_removed:
                AVAILABILITY_CHANGES.labels(change_type="dates_removed").inc()

            # Generar resultado
            result = {
                "valid": True,
                "dates_added": dates_added,
                "dates_removed": dates_removed,
                "requires_alert": bool(dates_removed),  # Alertar si se eliminan fechas
                "timestamp": datetime.now().isoformat(),
            }

            # Emitir evento si hay fechas removidas
            if result["requires_alert"]:
                await self.emit_event(
                    "availability_change",
                    {
                        "package_id": package_id,
                        "dates_removed": dates_removed,
                        "dates_added": dates_added,
                    },
                )

            return result

        except Exception as e:
            self.error_handler.log_error(
                "availability_validation_error",
                {"error": str(e), "package_id": package_id},
            )
            raise

        finally:
            ACTIVE_VALIDATIONS.dec()
            VALIDATION_LATENCY.labels(validation_type="availability").observe(
                (datetime.now() - start_time).total_seconds()
            )

    async def process_notification_queue(self):
        """Procesa la cola de notificaciones de cambios."""
        while True:
            try:
                notification = await self.notification_queue.get()

                if notification["type"] == "price_change":
                    await self.validate_price_change(
                        notification["package_id"],
                        notification["old_price"],
                        notification["new_price"],
                    )
                elif notification["type"] == "availability_change":
                    await self.validate_availability_change(
                        notification["package_id"],
                        notification["old_dates"],
                        notification["new_dates"],
                    )

                self.notification_queue.task_done()

            except Exception as e:
                self.error_handler.log_error(
                    "notification_processing_error", {"error": str(e)}
                )

            await asyncio.sleep(0.1)  # Evitar saturación de CPU

    async def start_monitoring(self):
        """Inicia el monitoreo en tiempo real."""
        self.logger.info("Iniciando monitoreo en tiempo real")
        asyncio.create_task(self.process_notification_queue())
