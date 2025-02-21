"""
Esquemas de datos para el sistema de presupuestos.

Este módulo define las estructuras de datos principales
utilizadas en el sistema de presupuestos.
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class ReconstructionStrategy(Enum):
    """Estrategias de reconstrucción de presupuestos."""
    
    PRESERVE_MARGIN = "preserve_margin"
    PRESERVE_PRICE = "preserve_price"
    ADJUST_PROPORTIONAL = "adjust_proportional"
    BEST_ALTERNATIVE = "best_alternative"


@dataclass
class BudgetItem:
    """Item individual dentro de un presupuesto."""
    
    id: str
    type: str
    category: str
    price: Decimal
    cost: Decimal
    rating: float
    availability: float
    dates: Dict[str, datetime]
    attributes: Dict[str, Any]

    def dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        data = asdict(self)
        # Convertir Decimal a float para serialización
        data["price"] = float(self.price)
        data["cost"] = float(self.cost)
        # Convertir datetime a ISO
        for key, value in data["dates"].items():
            data["dates"][key] = value.isoformat()
        return data


@dataclass
class Budget:
    """Presupuesto completo."""
    
    id: str
    items: List[BudgetItem]
    criteria: Dict[str, Any]
    dates: Dict[str, datetime]
    status: str = "active"
    locked: bool = False

    def dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        data = {
            "id": self.id,
            "items": [item.dict() for item in self.items],
            "criteria": self.criteria,
            "dates": {k: v.isoformat() for k, v in self.dates.items()},
            "status": self.status,
            "locked": self.locked
        }
        return data

    def copy(self) -> "Budget":
        """Crear una copia del presupuesto."""
        return Budget(
            id=self.id,
            items=[BudgetItem(**item.dict()) for item in self.items],
            criteria=self.criteria.copy(),
            dates=self.dates.copy(),
            status=self.status,
            locked=self.locked
        )


@dataclass
class AnalysisResult:
    """Resultado del análisis de impacto."""
    
    budget_id: str
    changes: Dict[str, Any]
    impact_level: float
    affected_items: List[str]
    recommendations: List[str]
    package_id: Optional[str]
    price_impact: float
    timestamp: datetime = datetime.now()

    def dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class SessionState:
    """Estado de una sesión de reconstrucción."""
    
    budget_id: str
    seller_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "active"
    stability_score: float = 1.0
    changes_applied: List[Dict[str, Any]] = None

    def __post_init__(self):
        """Inicializar campos opcionales."""
        if self.changes_applied is None:
            self.changes_applied = []

    def dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        data = asdict(self)
        data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        return data
