"""Models for authentication."""

from enum import Enum


class UserRole(str, Enum):
    """User role enumeration."""

    ADMIN = "ADMIN"
    AGENT = "AGENT"
    CLIENT = "CLIENT"
