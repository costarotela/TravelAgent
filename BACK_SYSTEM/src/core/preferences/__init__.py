"""Preference management system for travel packages."""

from .models import (
    PreferenceType,
    PreferenceValue,
    UserPreferences,
    VendorRule,
    FilterConfig,
)
from .manager import PreferenceManager

__all__ = [
    "PreferenceType",
    "PreferenceValue",
    "UserPreferences",
    "VendorRule",
    "FilterConfig",
    "PreferenceManager",
]
