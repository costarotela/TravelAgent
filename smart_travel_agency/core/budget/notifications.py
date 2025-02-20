"""
Sistema de notificaciones para cambios en presupuestos.

Este módulo maneja:
1. Notificaciones de cambios significativos
2. Alertas de impacto alto
3. Sugerencias de alternativas
4. Registro de eventos de reconstrucción
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from dataclasses import dataclass
from enum import Enum
from prometheus_client import Counter, Histogram

# Métricas
NOTIFICATION_COUNTER = Counter(
    "budget_notifications_total",
    "Number of budget notifications sent",
    ["type", "priority"],
)

NOTIFICATION_LATENCY = Histogram(
    "notification_processing_latency_seconds",
    "Latency of notification processing",
    ["type"],
)


class NotificationPriority(Enum):
    """Prioridad de notificaciones."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NotificationTemplate:
    """Template para notificaciones."""

    title: str
    message: str
    priority: NotificationPriority
    category: str

    def format(self, **kwargs) -> Dict[str, Any]:
        """Formatear template con datos específicos."""
        return {
            "title": self.title.format(**kwargs),
            "message": self.message.format(**kwargs),
            "priority": self.priority.value,
            "category": self.category,
            "timestamp": datetime.now().isoformat(),
        }


# Templates predefinidos
TEMPLATES = {
    "price_change": NotificationTemplate(
        title="Cambio significativo en precio",
        message="El precio del paquete {package_id} ha cambiado un {percentage}%",
        priority=NotificationPriority.HIGH,
        category="price",
    ),
    "availability_change": NotificationTemplate(
        title="Cambio en disponibilidad",
        message="La disponibilidad del paquete {package_id} ha cambiado a {new_availability}",
        priority=NotificationPriority.MEDIUM,
        category="availability",
    ),
    "reconstruction_needed": NotificationTemplate(
        title="Reconstrucción de presupuesto necesaria",
        message="El presupuesto {budget_id} requiere reconstrucción debido a {reason}",
        priority=NotificationPriority.HIGH,
        category="reconstruction",
    ),
    "alternatives_found": NotificationTemplate(
        title="Alternativas disponibles",
        message="Se encontraron {count} alternativas para el presupuesto {budget_id}",
        priority=NotificationPriority.MEDIUM,
        category="alternatives",
    ),
    "reconstruction_complete": NotificationTemplate(
        title="Reconstrucción completada",
        message="El presupuesto {budget_id} ha sido reconstruido usando estrategia {strategy}",
        priority=NotificationPriority.LOW,
        category="reconstruction",
    ),
}


class NotificationManager:
    """
    Gestor de notificaciones para cambios en presupuestos.
    """

    def __init__(self):
        """Inicializar gestor."""
        self.logger = logging.getLogger(__name__)
        self._handlers: Dict[str, List[callable]] = {}
        self._initialize_handlers()

    def _initialize_handlers(self):
        """Inicializar handlers por defecto."""
        # Handler para cambios de precio
        self.register_handler("price", self._handle_price_notification)

        # Handler para cambios de disponibilidad
        self.register_handler("availability", self._handle_availability_notification)

        # Handler para reconstrucciones
        self.register_handler(
            "reconstruction", self._handle_reconstruction_notification
        )

        # Handler para alternativas
        self.register_handler("alternatives", self._handle_alternatives_notification)

    def register_handler(self, category: str, handler: callable) -> None:
        """Registrar nuevo handler para categoría."""
        if category not in self._handlers:
            self._handlers[category] = []
        self._handlers[category].append(handler)

    async def notify(self, template_key: str, data: Dict[str, Any]) -> None:
        """
        Enviar notificación usando template.

        Args:
            template_key: Clave del template a usar
            data: Datos para formatear el template
        """
        try:
            template = TEMPLATES.get(template_key)
            if not template:
                raise ValueError(f"Template {template_key} no encontrado")

            notification = template.format(**data)

            # Procesar notificación
            await self._process_notification(notification)

            # Registrar métrica
            NOTIFICATION_COUNTER.labels(
                type=template_key, priority=notification["priority"]
            ).inc()

        except Exception as e:
            self.logger.error(f"Error enviando notificación: {e}")
            raise

    async def _process_notification(self, notification: Dict[str, Any]) -> None:
        """Procesar notificación según su categoría."""
        category = notification["category"]
        handlers = self._handlers.get(category, [])

        for handler in handlers:
            try:
                await handler(notification)
            except Exception as e:
                self.logger.error(f"Error en handler {handler.__name__}: {e}")

    async def _handle_price_notification(self, notification: Dict[str, Any]) -> None:
        """
        Manejar notificación de cambio de precio.

        Procesa cambios significativos en precios y determina
        acciones basadas en el impacto del cambio.
        """
        try:
            # Extraer datos relevantes
            title = notification["title"]
            message = notification["message"]
            priority = notification["priority"]
            timestamp = notification["timestamp"]

            # Registrar en log según prioridad
            if priority == NotificationPriority.HIGH.value:
                self.logger.warning(f"ALERTA DE PRECIO - {title}: {message}")

                # Enviar alerta a sistema de monitoreo
                await self._send_monitoring_alert(
                    {
                        "type": "price_change",
                        "severity": "high",
                        "title": title,
                        "message": message,
                        "timestamp": timestamp,
                    }
                )

            elif priority == NotificationPriority.MEDIUM.value:
                self.logger.info(f"Cambio de Precio - {title}: {message}")

            else:
                self.logger.debug(f"Actualización de Precio - {title}: {message}")

            # Registrar en historial
            await self._record_notification_history(
                {
                    "type": "price_change",
                    "title": title,
                    "message": message,
                    "priority": priority,
                    "timestamp": timestamp,
                }
            )

        except Exception as e:
            self.logger.error(f"Error procesando notificación de precio: {e}")
            raise

    async def _handle_availability_notification(
        self, notification: Dict[str, Any]
    ) -> None:
        """
        Manejar notificación de cambio de disponibilidad.

        Procesa cambios en disponibilidad y actualiza
        estados relacionados.
        """
        try:
            # Extraer datos relevantes
            title = notification["title"]
            message = notification["message"]
            priority = notification["priority"]
            timestamp = notification["timestamp"]

            # Registrar en log según prioridad
            if priority == NotificationPriority.HIGH.value:
                self.logger.warning(f"ALERTA DE DISPONIBILIDAD - {title}: {message}")

                # Enviar alerta si disponibilidad es crítica
                await self._send_monitoring_alert(
                    {
                        "type": "availability_change",
                        "severity": "high",
                        "title": title,
                        "message": message,
                        "timestamp": timestamp,
                    }
                )

            else:
                self.logger.info(f"Cambio de Disponibilidad - {title}: {message}")

            # Registrar en historial
            await self._record_notification_history(
                {
                    "type": "availability_change",
                    "title": title,
                    "message": message,
                    "priority": priority,
                    "timestamp": timestamp,
                }
            )

        except Exception as e:
            self.logger.error(f"Error procesando notificación de disponibilidad: {e}")
            raise

    async def _handle_reconstruction_notification(
        self, notification: Dict[str, Any]
    ) -> None:
        """
        Manejar notificación de reconstrucción.

        Procesa eventos de reconstrucción y coordina
        acciones relacionadas.
        """
        try:
            # Extraer datos relevantes
            title = notification["title"]
            message = notification["message"]
            priority = notification["priority"]
            timestamp = notification["timestamp"]

            # Registrar en log según prioridad
            if priority == NotificationPriority.HIGH.value:
                self.logger.warning(f"RECONSTRUCCIÓN CRÍTICA - {title}: {message}")

                # Enviar alerta si la reconstrucción es crítica
                await self._send_monitoring_alert(
                    {
                        "type": "reconstruction",
                        "severity": "high",
                        "title": title,
                        "message": message,
                        "timestamp": timestamp,
                    }
                )

            elif priority == NotificationPriority.MEDIUM.value:
                self.logger.info(f"Reconstrucción en Proceso - {title}: {message}")

            else:
                self.logger.info(f"Reconstrucción Completada - {title}: {message}")

            # Registrar en historial
            await self._record_notification_history(
                {
                    "type": "reconstruction",
                    "title": title,
                    "message": message,
                    "priority": priority,
                    "timestamp": timestamp,
                }
            )

        except Exception as e:
            self.logger.error(f"Error procesando notificación de reconstrucción: {e}")
            raise

    async def _handle_alternatives_notification(
        self, notification: Dict[str, Any]
    ) -> None:
        """
        Manejar notificación de alternativas.

        Procesa notificaciones sobre alternativas encontradas
        y coordina su presentación.
        """
        try:
            # Extraer datos relevantes
            title = notification["title"]
            message = notification["message"]
            priority = notification["priority"]
            timestamp = notification["timestamp"]

            # Registrar en log
            self.logger.info(f"Alternativas Encontradas - {title}: {message}")

            # Si hay alternativas prioritarias, elevar importancia
            if priority == NotificationPriority.HIGH.value:
                await self._send_monitoring_alert(
                    {
                        "type": "alternatives",
                        "severity": "medium",
                        "title": title,
                        "message": message,
                        "timestamp": timestamp,
                    }
                )

            # Registrar en historial
            await self._record_notification_history(
                {
                    "type": "alternatives",
                    "title": title,
                    "message": message,
                    "priority": priority,
                    "timestamp": timestamp,
                }
            )

        except Exception as e:
            self.logger.error(f"Error procesando notificación de alternativas: {e}")
            raise

    async def _send_monitoring_alert(self, alert_data: Dict[str, Any]) -> None:
        """Enviar alerta al sistema de monitoreo."""
        # TODO: Integrar con sistema de monitoreo real
        self.logger.info(f"Alerta enviada a monitoreo: {alert_data}")

    async def _record_notification_history(
        self, notification_data: Dict[str, Any]
    ) -> None:
        """Registrar notificación en historial."""
        # TODO: Implementar persistencia real
        self.logger.debug(f"Notificación registrada: {notification_data}")


# Instancia global
notification_manager = NotificationManager()


async def get_notification_manager() -> NotificationManager:
    """Obtener instancia única del gestor."""
    return notification_manager
