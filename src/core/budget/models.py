"""Models for budget management."""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ..providers import TravelPackage


class BudgetStatus(str, Enum):
    """Status of a budget."""
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class BudgetVersion(BaseModel):
    """Version of a budget with changes and metadata."""
    version: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    comment: str
    changes: Dict[str, str]
    packages: List[TravelPackage]
    total_price: float
    currency: str
    markup_percentage: float = 0.0
    final_price: float


class Budget(BaseModel):
    """Budget model with versioning support."""
    id: str
    client_name: str
    client_email: str
    status: BudgetStatus = BudgetStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = None
    current_version: int
    versions: List[BudgetVersion]
    notes: Optional[str] = None
    metadata: Dict[str, str] = Field(default_factory=dict)


class BudgetTemplate(BaseModel):
    """Template for creating budgets."""
    id: str
    name: str
    description: str
    markup_percentage: float
    default_validity_days: int
    email_template: str
    metadata: Dict[str, str] = Field(default_factory=dict)
