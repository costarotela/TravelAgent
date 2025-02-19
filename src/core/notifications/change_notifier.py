"""Change notifier for OLA updates."""

import logging
from typing import Dict, List, Optional

from .manager import NotificationManager
from .models import NotificationPriority, NotificationType

logger = logging.getLogger(__name__)


class ChangeNotifier:
    """Notifier for OLA changes."""

    def __init__(
        self,
        notification_manager: NotificationManager,
        threshold: int = 5,
        recipients: Optional[List[str]] = None,
    ):
        """Initialize change notifier.

        Args:
            notification_manager: Notification manager instance
            threshold: Minimum number of changes to trigger notification
            recipients: List of recipient IDs to notify
        """
        self.notification_manager = notification_manager
        self.threshold = threshold
        self.recipients = recipients or ["alertas@tuempresa.com"]

    def process_report(self, report: Dict) -> None:
        """Process a change report and send notifications if needed.

        Args:
            report: Change report from OLA updater
        """
        stats = report.get("stats", {})
        total_nuevos = stats.get("total_nuevos", 0)
        total_actualizados = stats.get("total_actualizados", 0)
        total_eliminados = stats.get("total_eliminados", 0)
        total_changes = total_nuevos + total_actualizados

        logger.info(
            f"Procesando reporte de cambios: {total_changes} cambios detectados"
        )

        # Notificar cambios significativos si superan el umbral
        if total_changes >= self.threshold:
            self._notify_significant_changes(
                total_nuevos, total_actualizados, total_eliminados
            )

        # Notificar cambios específicos si hay alguno
        if total_nuevos > 0:
            self._notify_new_packages(total_nuevos, report.get("nuevos", []))
        if total_actualizados > 0:
            self._notify_updated_packages(
                total_actualizados, report.get("actualizados", [])
            )
        if total_eliminados > 0:
            self._notify_deleted_packages(
                total_eliminados, report.get("eliminados", [])
            )

    def _notify_significant_changes(
        self, nuevos: int, actualizados: int, eliminados: int
    ) -> None:
        """Send notification for significant changes.

        Args:
            nuevos: Number of new packages
            actualizados: Number of updated packages
            eliminados: Number of deleted packages
        """
        for recipient_id in self.recipients:
            self.notification_manager.create_notification(
                type=NotificationType.OLA_SIGNIFICANT_CHANGES,
                recipient_id=recipient_id,
                priority=NotificationPriority.HIGH,
                context={
                    "total_nuevos": nuevos,
                    "total_actualizados": actualizados,
                    "total_eliminados": eliminados,
                },
                metadata={
                    "source": "ola_updater",
                    "change_type": "significant",
                },
            )

    def _notify_new_packages(self, total: int, packages: List[Dict]) -> None:
        """Send notification for new packages.

        Args:
            total: Number of new packages
            packages: List of new package details
        """
        for recipient_id in self.recipients:
            self.notification_manager.create_notification(
                type=NotificationType.OLA_NEW_PACKAGES,
                recipient_id=recipient_id,
                priority=NotificationPriority.MEDIUM,
                context={
                    "total": total,
                    "packages": packages[:5],  # Limitar a 5 ejemplos
                    "has_more": len(packages) > 5,
                },
                metadata={
                    "source": "ola_updater",
                    "change_type": "new_packages",
                },
            )

    def _notify_updated_packages(self, total: int, packages: List[Dict]) -> None:
        """Send notification for updated packages.

        Args:
            total: Number of updated packages
            packages: List of updated package details
        """
        for recipient_id in self.recipients:
            self.notification_manager.create_notification(
                type=NotificationType.OLA_UPDATED_PACKAGES,
                recipient_id=recipient_id,
                priority=NotificationPriority.MEDIUM,
                context={
                    "total": total,
                    "packages": packages[:5],  # Limitar a 5 ejemplos
                    "has_more": len(packages) > 5,
                },
                metadata={
                    "source": "ola_updater",
                    "change_type": "updated_packages",
                },
            )

    def _notify_deleted_packages(self, total: int, packages: List[Dict]) -> None:
        """Send notification for deleted packages.

        Args:
            total: Number of deleted packages
            packages: List of deleted package details
        """
        for recipient_id in self.recipients:
            self.notification_manager.create_notification(
                type=NotificationType.OLA_DELETED_PACKAGES,
                recipient_id=recipient_id,
                priority=NotificationPriority.MEDIUM,
                context={
                    "total": total,
                    "packages": packages[:5],  # Limitar a 5 ejemplos
                    "has_more": len(packages) > 5,
                },
                metadata={
                    "source": "ola_updater",
                    "change_type": "deleted_packages",
                },
            )
