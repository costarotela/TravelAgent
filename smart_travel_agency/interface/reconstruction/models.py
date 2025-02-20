"""
Modelos para el sistema de reconstrucción de presupuestos.
Permite recrear presupuestos previos con datos actualizados.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

@dataclass
class PriceHistory:
    """Historial de precios de un ítem."""
    item_id: str
    provider_id: str
    price_points: List[Dict[str, Decimal]] = field(default_factory=list)
    
    def add_price(self, price: Decimal, timestamp: datetime) -> None:
        """Agrega un punto de precio al historial."""
        self.price_points.append({
            "price": price,
            "timestamp": timestamp
        })
    
    def get_price_at(self, target_time: datetime) -> Optional[Decimal]:
        """Obtiene el precio más cercano a una fecha específica."""
        if not self.price_points:
            return None
            
        # Encuentra el precio más cercano a la fecha objetivo
        closest = min(
            self.price_points,
            key=lambda x: abs((x["timestamp"] - target_time).total_seconds())
        )
        return closest["price"]

@dataclass
class BudgetSnapshot:
    """Captura del estado de un presupuesto en un momento específico."""
    budget_id: UUID
    timestamp: datetime
    items: Dict[str, dict] = field(default_factory=dict)
    total: Decimal = Decimal("0")
    metadata: Dict[str, str] = field(default_factory=dict)
    
    def add_item(self,
                 item_id: str,
                 provider_id: str,
                 price: Decimal,
                 quantity: int = 1,
                 **kwargs) -> None:
        """Agrega un ítem a la captura."""
        self.items[item_id] = {
            "provider_id": provider_id,
            "price": price,
            "quantity": quantity,
            **kwargs
        }
        self.update_total()
    
    def update_total(self) -> None:
        """Actualiza el total del presupuesto."""
        self.total = sum(
            item["price"] * item["quantity"]
            for item in self.items.values()
        )

@dataclass
class ReconstructionData:
    """Datos necesarios para reconstruir un presupuesto."""
    original_snapshot: BudgetSnapshot
    price_histories: Dict[str, PriceHistory] = field(default_factory=dict)
    provider_states: Dict[str, dict] = field(default_factory=dict)
    
    def add_price_history(self, history: PriceHistory) -> None:
        """Agrega historial de precios para un ítem."""
        self.price_histories[history.item_id] = history
    
    def set_provider_state(self,
                          provider_id: str,
                          state_data: dict) -> None:
        """Establece el estado de un proveedor."""
        self.provider_states[provider_id] = state_data
    
    def get_item_price(self,
                      item_id: str,
                      target_time: datetime) -> Optional[Decimal]:
        """Obtiene el precio de un ítem en un momento específico."""
        if history := self.price_histories.get(item_id):
            return history.get_price_at(target_time)
        return None
