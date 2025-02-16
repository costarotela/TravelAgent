"""Notification manager for handling all notification operations."""
import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Union
from uuid import uuid4

from ..budget.models import Budget, BudgetStatus
from .models import (
    Notification,
    NotificationChannel,
    NotificationPreference,
    NotificationPriority,
    NotificationTemplate,
    NotificationType,
)
from .providers import EmailProvider, PushProvider, SMSProvider, WebhookProvider

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manager for handling notifications across different channels."""

    def __init__(
        self,
        email_provider: Optional[EmailProvider] = None,
        sms_provider: Optional[SMSProvider] = None,
        push_provider: Optional[PushProvider] = None,
        webhook_provider: Optional[WebhookProvider] = None,
    ):
        """Initialize notification manager.
        
        Args:
            email_provider: Provider for email notifications
            sms_provider: Provider for SMS notifications
            push_provider: Provider for push notifications
            webhook_provider: Provider for webhook notifications
        """
        self.providers = {
            NotificationChannel.EMAIL: email_provider,
            NotificationChannel.SMS: sms_provider,
            NotificationChannel.PUSH: push_provider,
            NotificationChannel.WEBHOOK: webhook_provider,
        }
        self._templates: Dict[str, NotificationTemplate] = {}
        self._preferences: Dict[str, NotificationPreference] = {}

    def create_notification(
        self,
        type: NotificationType,
        recipient_id: str,
        template_id: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        context: Optional[Dict] = None,
        scheduled_for: Optional[datetime] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Notification:
        """Create a new notification.
        
        Args:
            type: Type of notification
            recipient_id: ID of recipient
            template_id: Optional template ID to use
            priority: Priority level
            context: Optional context for template rendering
            scheduled_for: Optional scheduled time
            metadata: Optional metadata
        
        Returns:
            Created Notification object
        """
        # Get recipient preferences
        preferences = self._preferences.get(recipient_id)
        if not preferences:
            raise ValueError(f"No preferences found for user {recipient_id}")

        # Check if notification type is disabled
        if type in preferences.disabled_types:
            logger.info(
                f"Notification type {type} is disabled for user {recipient_id}"
            )
            return None

        # Get channels for notification type
        channels = preferences.channels.get(type, [NotificationChannel.EMAIL])

        # Get template if specified
        template = self._templates.get(template_id) if template_id else None
        
        # Create notification
        notification = Notification(
            id=str(uuid4()),
            type=type,
            priority=priority,
            subject=self._render_template(
                template.subject if template else "",
                context
            ),
            body=self._render_template(
                template.body if template else "",
                context
            ),
            recipient_email=preferences.email,
            recipient_phone=preferences.phone,
            channels=channels,
            scheduled_for=scheduled_for,
            metadata=metadata or {}
        )

        logger.info(
            f"Created {priority} notification {notification.id} "
            f"of type {type} for user {recipient_id}"
        )
        return notification

    def send_notification(
        self,
        notification: Notification,
        force: bool = False
    ) -> bool:
        """Send a notification through configured channels.
        
        Args:
            notification: Notification to send
            force: If True, ignore quiet hours
        
        Returns:
            True if sent successfully
        """
        if not force and self._is_quiet_hours(notification):
            logger.info(
                f"Notification {notification.id} delayed due to quiet hours"
            )
            return False

        success = True
        for channel in notification.channels:
            provider = self.providers.get(channel)
            if not provider:
                logger.warning(f"No provider configured for channel {channel}")
                success = False
                continue

            try:
                provider.send(notification)
                logger.info(
                    f"Sent notification {notification.id} via {channel}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to send notification {notification.id} "
                    f"via {channel}: {e}"
                )
                notification.error = str(e)
                success = False

        notification.status = "sent" if success else "failed"
        notification.sent_at = datetime.utcnow() if success else None
        return success

    def notify_budget_update(
        self,
        budget: Budget,
        old_status: Optional[BudgetStatus] = None
    ) -> List[Notification]:
        """Create notifications for budget updates.
        
        Args:
            budget: Updated budget
            old_status: Previous status if status changed
        
        Returns:
            List of created notifications
        """
        notifications = []

        # Determine notification type
        if old_status is None:
            ntype = NotificationType.BUDGET_CREATED
            priority = NotificationPriority.MEDIUM
        elif budget.status != old_status:
            ntype = {
                BudgetStatus.APPROVED: NotificationType.BUDGET_APPROVED,
                BudgetStatus.REJECTED: NotificationType.BUDGET_REJECTED,
                BudgetStatus.EXPIRED: NotificationType.BUDGET_EXPIRED,
            }.get(budget.status, NotificationType.BUDGET_UPDATED)
            priority = NotificationPriority.HIGH
        else:
            ntype = NotificationType.BUDGET_UPDATED
            priority = NotificationPriority.MEDIUM

        # Create notification for client
        client_notification = self.create_notification(
            type=ntype,
            recipient_id=budget.client_email,
            template_id=f"{ntype}_client",
            priority=priority,
            context={"budget": budget},
            metadata={"budget_id": budget.id}
        )
        if client_notification:
            notifications.append(client_notification)

        # Create notification for internal users
        internal_notification = self.create_notification(
            type=ntype,
            recipient_id="internal",
            template_id=f"{ntype}_internal",
            priority=priority,
            context={"budget": budget},
            metadata={"budget_id": budget.id}
        )
        if internal_notification:
            notifications.append(internal_notification)

        return notifications

    def register_template(
        self,
        template: NotificationTemplate
    ) -> None:
        """Register a new notification template.
        
        Args:
            template: Template to register
        """
        self._templates[template.id] = template
        logger.info(f"Registered template {template.id}")

    def set_preferences(
        self,
        preferences: NotificationPreference
    ) -> None:
        """Set notification preferences for a user.
        
        Args:
            preferences: User's notification preferences
        """
        self._preferences[preferences.user_id] = preferences
        logger.info(f"Updated preferences for user {preferences.user_id}")

    def _is_quiet_hours(self, notification: Notification) -> bool:
        """Check if current time is within quiet hours."""
        if not notification.recipient_email:
            return False

        preferences = self._preferences.get(notification.recipient_email)
        if not preferences or not (
            preferences.quiet_hours_start and preferences.quiet_hours_end
        ):
            return False

        current_hour = datetime.utcnow().hour
        start = preferences.quiet_hours_start
        end = preferences.quiet_hours_end

        if start <= end:
            return start <= current_hour < end
        else:  # Handles overnight quiet hours
            return current_hour >= start or current_hour < end

    def _render_template(
        self,
        template: str,
        context: Optional[Dict] = None
    ) -> str:
        """Render a template with given context."""
        if not template:
            return ""
        if not context:
            return template
            
        # Simple template rendering
        result = template
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result
