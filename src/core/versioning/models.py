"""Models for budget versioning system."""

from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    """Types of changes in a budget version."""

    PRICE = "price"  # Cambios en precios
    PACKAGE = "package"  # Cambios en paquetes
    MARGIN = "margin"  # Cambios en márgenes
    DISCOUNT = "discount"  # Cambios en descuentos
    RULE = "rule"  # Cambios en reglas
    PREFERENCE = "preference"  # Cambios en preferencias
    METADATA = "metadata"  # Cambios en metadatos


class ChangeStatus(str, Enum):
    """Status of a change."""

    PENDING = "pending"  # Cambio pendiente de aplicar
    APPLIED = "applied"  # Cambio aplicado
    REJECTED = "rejected"  # Cambio rechazado
    REVERTED = "reverted"  # Cambio revertido


class Change(BaseModel):
    """A single change in a budget version."""

    id: str
    type: ChangeType
    field: str
    old_value: Any
    new_value: Any
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: ChangeStatus = ChangeStatus.PENDING
    author: str
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Version(BaseModel):
    """A version of a budget."""

    id: str
    budget_id: str
    number: int
    parent_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    changes: List[Change]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    status: str = "active"  # active, archived, deleted
    is_base: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Branch(BaseModel):
    """A branch of versions."""

    id: str
    budget_id: str
    name: str
    description: Optional[str] = None
    base_version_id: str
    versions: List[str]  # Lista de IDs de versiones
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    status: str = "active"  # active, archived, merged
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MergeStrategy(str, Enum):
    """Strategies for merging versions."""

    OURS = "ours"  # Usar nuestros cambios en conflictos
    THEIRS = "theirs"  # Usar sus cambios en conflictos
    MANUAL = "manual"  # Resolver conflictos manualmente


class MergeResult(BaseModel):
    """Result of a merge operation."""

    success: bool
    merged_version_id: Optional[str] = None
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    changes_applied: List[Change] = Field(default_factory=list)
    changes_rejected: List[Change] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VersionDiff(BaseModel):
    """Difference between two versions."""

    base_version_id: str
    target_version_id: str
    changes: List[Change]
    summary: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VersionGraph(BaseModel):
    """Graph representation of version history."""

    budget_id: str
    nodes: List[Dict[str, Any]]  # Versiones
    edges: List[Dict[str, Any]]  # Relaciones entre versiones
    branches: List[Dict[str, Any]]  # Ramas
    metadata: Dict[str, Any] = Field(default_factory=dict)
