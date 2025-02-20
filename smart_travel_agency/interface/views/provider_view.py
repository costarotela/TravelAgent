"""
Vista de proveedores para la interfaz de vendedor.
Maneja la visualización y actualización de datos de proveedores en tiempo real.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class ProviderItemView:
    """Representa un ítem disponible de un proveedor."""
    item_id: str
    name: str
    category: str
    current_price: Decimal
    last_update: datetime
    availability: bool = True
    restrictions: List[str] = field(default_factory=list)
    
    @property
    def is_price_fresh(self) -> bool:
        """Verifica si el precio está actualizado (menos de 1 hora)."""
        return (datetime.now() - self.last_update).total_seconds() < 3600

@dataclass
class ProviderView:
    """Vista principal de un proveedor."""
    provider_id: str
    name: str
    items: Dict[str, ProviderItemView] = field(default_factory=dict)
    status: str = "active"
    connection_errors: List[str] = field(default_factory=list)
    
    def add_item(self, 
                 item_id: str,
                 name: str,
                 category: str,
                 price: Decimal) -> ProviderItemView:
        """Agrega o actualiza un ítem del proveedor."""
        item = ProviderItemView(
            item_id=item_id,
            name=name,
            category=category,
            current_price=price,
            last_update=datetime.now()
        )
        self.items[item_id] = item
        return item
    
    def update_item_price(self,
                         item_id: str,
                         new_price: Decimal) -> bool:
        """Actualiza el precio de un ítem."""
        if item := self.items.get(item_id):
            item.current_price = new_price
            item.last_update = datetime.now()
            return True
        return False
    
    def set_item_availability(self,
                            item_id: str,
                            available: bool) -> None:
        """Actualiza la disponibilidad de un ítem."""
        if item := self.items.get(item_id):
            item.availability = available
    
    def add_restriction(self,
                       item_id: str,
                       restriction: str) -> None:
        """Agrega una restricción a un ítem."""
        if item := self.items.get(item_id):
            if restriction not in item.restrictions:
                item.restrictions.append(restriction)
    
    def get_available_items(self) -> List[ProviderItemView]:
        """Retorna todos los ítems disponibles."""
        return [
            item for item in self.items.values()
            if item.availability
        ]
    
    def get_items_by_category(self, category: str) -> List[ProviderItemView]:
        """Retorna ítems filtrados por categoría."""
        return [
            item for item in self.items.values()
            if item.category == category
        ]
    
    def add_error(self, error: str) -> None:
        """Registra un error de conexión."""
        self.connection_errors.append(error)
        if len(self.connection_errors) > 5:
            self.status = "error"
