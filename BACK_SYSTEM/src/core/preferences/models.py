"""Models for preference management system."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field


class PreferenceType(str, Enum):
    """Types of preferences that can be stored."""

    BUDGET = "budget"  # Preferencias de presupuesto (márgenes, límites)
    TRAVEL = "travel"  # Preferencias de viaje (destinos, fechas)
    NOTIFICATION = "notification"  # Preferencias de notificación
    DISPLAY = "display"  # Preferencias de visualización
    VENDOR = "vendor"  # Preferencias del vendedor
    FILTER = "filter"  # Filtros personalizados


class PreferenceValue(BaseModel):
    """Value of a preference with metadata."""

    value: Any
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    source: str = "user"  # user, system, learned
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserPreferences(BaseModel):
    """Preferences for a specific user."""

    user_id: str
    preferences: Dict[PreferenceType, Dict[str, PreferenceValue]]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VendorRule(BaseModel):
    """Rule defined by a vendor."""

    name: str
    description: str
    preference_type: PreferenceType
    conditions: Dict[str, Any]
    actions: Dict[str, Any]
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FilterConfig(BaseModel):
    """Configuration for automatic filtering."""

    name: str
    description: str
    filter_type: str  # price, date, destination, etc.
    criteria: Dict[str, Any]
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
