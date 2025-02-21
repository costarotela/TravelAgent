"""
Sistema de notificaciones para el Smart Travel Agent.
Maneja la creación, gestión y distribución de notificaciones.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass


class NotificationType(Enum):
    """Tipos de notificaciones soportadas por el sistema."""
    PRICE_CHANGE = "Cambio de Precio"
    AVAILABILITY = "Cambio de Disponibilidad"
    PACKAGE_OFFER = "Nueva Oferta de Paquete"
    SEASON_ALERT = "Alerta de Temporada"
    PROVIDER_UPDATE = "Actualización de Proveedor"


class NotificationSeverity(Enum):
    """Niveles de severidad para las notificaciones."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Notification:
    """
    Representa una notificación en el sistema.
    
    Attributes:
        type: Tipo de notificación
        message: Mensaje descriptivo
        item_id: ID del item relacionado
        severity: Nivel de severidad
        timestamp: Momento de creación
        data: Datos adicionales específicos del tipo de notificación
        read: Estado de lectura
    """
    type: NotificationType
    message: str
    item_id: str
    severity: NotificationSeverity
    timestamp: datetime
    data: Optional[Dict] = None
    read: bool = False

    def mark_as_read(self) -> None:
        """Marca la notificación como leída."""
        self.read = True

    def to_dict(self) -> Dict:
        """Convierte la notificación a diccionario para serialización."""
        return {
            "type": self.type.value,
            "message": self.message,
            "item_id": self.item_id,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data or {},
            "read": self.read
        }


class NotificationManager:
    """
    Gestor central de notificaciones.
    Maneja la creación, almacenamiento y distribución de notificaciones.
    """
    def __init__(self):
        self.notifications: List[Notification] = []
        self.subscribers: List[Callable[[Notification], None]] = []
        
    def add_notification(self, notification: Notification) -> None:
        """
        Agrega una nueva notificación y notifica a los suscriptores.
        
        Args:
            notification: Notificación a agregar
        """
        self.notifications.append(notification)
        self._notify_subscribers(notification)
    
    def subscribe(self, callback: Callable[[Notification], None]) -> None:
        """
        Suscribe una función para recibir notificaciones.
        
        Args:
            callback: Función a llamar cuando hay una nueva notificación
        """
        self.subscribers.append(callback)
    
    def _notify_subscribers(self, notification: Notification) -> None:
        """
        Notifica a todos los suscriptores sobre una nueva notificación.
        
        Args:
            notification: Notificación a distribuir
        """
        for subscriber in self.subscribers:
            subscriber(notification)
    
    def get_unread(self) -> List[Notification]:
        """Retorna todas las notificaciones no leídas."""
        return [n for n in self.notifications if not n.read]
    
    def get_by_severity(self, severity: NotificationSeverity) -> List[Notification]:
        """
        Retorna notificaciones filtradas por severidad.
        
        Args:
            severity: Nivel de severidad a filtrar
        """
        return [n for n in self.notifications if n.severity == severity]
    
    def get_by_type(self, type: NotificationType) -> List[Notification]:
        """
        Retorna notificaciones filtradas por tipo.
        
        Args:
            type: Tipo de notificación a filtrar
        """
        return [n for n in self.notifications if n.type == type]
    
    def mark_all_as_read(self) -> None:
        """Marca todas las notificaciones como leídas."""
        for notification in self.notifications:
            notification.mark_as_read()
    
    def clear_old_notifications(self, days: int = 30) -> None:
        """
        Elimina notificaciones más antiguas que el número de días especificado.
        
        Args:
            days: Días a mantener (default: 30)
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        self.notifications = [
            n for n in self.notifications 
            if n.timestamp.timestamp() > cutoff
        ]
