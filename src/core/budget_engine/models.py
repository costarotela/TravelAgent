"""Models for budget update engine."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field

from ..collectors.models import PackageData


class ChangeType(str, Enum):
    """Types of changes that can occur in a budget."""

    PRICE_INCREASE = "price_increase"
    PRICE_DECREASE = "price_decrease"
    AVAILABILITY_CHANGE = "availability_change"
    DATES_CHANGE = "dates_change"
    PACKAGE_REMOVED = "package_removed"
    PACKAGE_ADDED = "package_added"
    DETAILS_CHANGE = "details_change"


class BudgetRule(BaseModel):
    """Rule for budget adjustments."""

    name: str
    description: str
    condition: Dict[str, Any]  # e.g. {"type": "price_increase", "threshold": 10}
    action: Dict[str, Any]  # e.g. {"type": "apply_discount", "value": 5}
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BudgetChange(BaseModel):
    """Represents a change in a budget."""

    change_type: ChangeType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    old_value: Any
    new_value: Any
    package_id: str
    provider: str
    applied_rules: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BudgetVersion(BaseModel):
    """A version of a budget."""

    version: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    packages: List[PackageData]
    total_price: Decimal
    currency: str
    markup_percentage: float
    final_price: Decimal
    changes: List[BudgetChange] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Budget(BaseModel):
    """Complete budget with version history."""

    id: str
    client_name: str
    client_email: str
    current_version: int
    versions: List[BudgetVersion]
    valid_until: datetime
    status: str = "draft"  # draft, pending, approved, rejected, expired
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def current(self) -> BudgetVersion:
        """Get current version of budget."""
        return self.versions[self.current_version - 1]

    @property
    def total_changes(self) -> int:
        """Get total number of changes across all versions."""
        return sum(len(version.changes) for version in self.versions)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": self.id,
            "client_name": self.client_name,
            "client_email": self.client_email,
            "current_version": self.current_version,
            "versions": [v.dict() for v in self.versions],
            "valid_until": self.valid_until.isoformat(),
            "status": self.status,
            "notes": self.notes,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
