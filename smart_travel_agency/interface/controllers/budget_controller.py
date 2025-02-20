"""
Controlador de presupuestos que conecta la vista con los datos del sistema.
"""
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from ..session import SessionManager
from ..views.budget_view import BudgetView

class BudgetController:
    """Controlador principal para operaciones de presupuesto."""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self._active_views: Dict[UUID, BudgetView] = {}
        
    def create_budget_view(self, session_id: UUID) -> Optional[BudgetView]:
        """Crea una nueva vista de presupuesto para una sesión."""
        if session_state := self.session_manager.get_session(session_id):
            view = BudgetView(session_state)
            self._active_views[session_id] = view
            return view
        return None

    def get_budget_view(self, session_id: UUID) -> Optional[BudgetView]:
        """Recupera una vista existente."""
        return self._active_views.get(session_id)

    def add_budget_item(self,
                       session_id: UUID,
                       item_data: dict) -> bool:
        """Agrega un ítem al presupuesto."""
        if view := self._active_views.get(session_id):
            try:
                view.add_item(
                    item_id=item_data["id"],
                    description=item_data["description"],
                    provider_id=item_data["provider_id"],
                    price=Decimal(str(item_data["price"]))
                )
                return True
            except (KeyError, ValueError):
                return False
        return False

    def update_item_price(self,
                         session_id: UUID,
                         item_id: str,
                         new_price: float) -> bool:
        """Actualiza el precio de un ítem."""
        if view := self._active_views.get(session_id):
            try:
                view.update_item_price(item_id, Decimal(str(new_price)))
                return True
            except ValueError:
                return False
        return False

    def validate_budget(self, session_id: UUID) -> bool:
        """Valida todo el presupuesto."""
        if view := self._active_views.get(session_id):
            return all(
                view.validate_item(item_id) 
                for item_id in view._items
            )
        return False

    def close_budget_view(self, session_id: UUID) -> None:
        """Cierra una vista de presupuesto."""
        if view := self._active_views.pop(session_id, None):
            # Procesar cambios pendientes antes de cerrar
            modified = view.get_modified_items()
            if modified:
                session_state = view.session
                for item in modified:
                    session_state.queue_update({
                        "item_id": item.item_id,
                        "price": float(item.current_price),
                        "quantity": item.quantity
                    })
