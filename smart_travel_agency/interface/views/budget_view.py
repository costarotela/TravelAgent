"""
Vista de presupuestos para la interfaz de vendedor.
Maneja la presentación y edición de presupuestos en tiempo real.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from ..session import SessionState

@dataclass
class BudgetItemView:
    """Representa un ítem de presupuesto en la vista."""
    item_id: str
    description: str
    provider_id: str
    base_price: Decimal
    current_price: Decimal
    quantity: int = 1
    is_modified: bool = False
    validation_errors: List[str] = field(default_factory=list)

    @property
    def total_price(self) -> Decimal:
        return self.current_price * self.quantity

class BudgetView:
    """Controlador principal de la vista de presupuestos."""
    
    def __init__(self, session_state: SessionState):
        self.session = session_state
        self._items: Dict[str, BudgetItemView] = {}
        
    def add_item(self, 
                 item_id: str,
                 description: str,
                 provider_id: str,
                 price: Decimal) -> BudgetItemView:
        """Agrega un nuevo ítem al presupuesto."""
        item = BudgetItemView(
            item_id=item_id,
            description=description,
            provider_id=provider_id,
            base_price=price,
            current_price=price
        )
        self._items[item_id] = item
        return item

    def update_item_price(self, 
                         item_id: str, 
                         new_price: Decimal) -> None:
        """Actualiza el precio de un ítem."""
        if item := self._items.get(item_id):
            item.current_price = new_price
            item.is_modified = True
            self.session.session.add_modification(
                item_id, 
                {"price": float(new_price)}
            )

    def update_quantity(self, 
                       item_id: str, 
                       quantity: int) -> None:
        """Actualiza la cantidad de un ítem."""
        if item := self._items.get(item_id):
            item.quantity = quantity
            self.session.session.add_modification(
                item_id, 
                {"quantity": quantity}
            )

    def get_total(self) -> Decimal:
        """Calcula el total del presupuesto."""
        return sum(item.total_price for item in self._items.values())

    def get_modified_items(self) -> List[BudgetItemView]:
        """Retorna los ítems modificados."""
        return [item for item in self._items.values() if item.is_modified]

    def validate_item(self, item_id: str) -> bool:
        """Valida un ítem específico."""
        item = self._items.get(item_id)
        if not item:
            return False

        item.validation_errors.clear()
        
        # Validaciones básicas
        if item.current_price < Decimal("0"):
            item.validation_errors.append("El precio no puede ser negativo")
        
        if item.quantity < 1:
            item.validation_errors.append("La cantidad debe ser al menos 1")
            
        # Validación con datos del proveedor
        provider_data = self.session.provider_data.get(item.provider_id, {})
        if max_price := provider_data.get("max_price"):
            if item.current_price > Decimal(str(max_price)):
                item.validation_errors.append("Precio excede el máximo permitido")

        return not bool(item.validation_errors)
