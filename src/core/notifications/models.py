"""Models for notification system."""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    """Types of notifications."""
    BUDGET_CREATED = "budget_created"
    BUDGET_UPDATED = "budget_updated"
    BUDGET_APPROVED = "budget_approved"
    BUDGET_REJECTED = "budget_rejected"
    BUDGET_EXPIRED = "budget_expired"
    PRICE_CHANGE = "price_change"
    AVAILABILITY_CHANGE = "availability_change"
    CUSTOM = "custom"


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(str, Enum):
    """Available notification channels."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"


class NotificationTemplate(BaseModel):
    """Template for notifications."""
    id: str
    type: NotificationType
    name: str
    subject: str
    body: str
    channels: List[NotificationChannel]
    metadata: Dict[str, str] = Field(default_factory=dict)


class Notification(BaseModel):
    """Notification model."""
    id: str
    type: NotificationType
    priority: NotificationPriority
    subject: str
    body: str
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    channels: List[NotificationChannel]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    status: str = "pending"
    error: Optional[str] = None
    metadata: Dict[str, str] = Field(default_factory=dict)


class NotificationPreference(BaseModel):
    """User preferences for notifications."""
    user_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    channels: Dict[NotificationType, List[NotificationChannel]]
    quiet_hours_start: Optional[int] = None
    quiet_hours_end: Optional[int] = None
    disabled_types: List[NotificationType] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)
