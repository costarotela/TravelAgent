"""
Controlador para manejar la interacción con proveedores en la interfaz.
"""
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from ..session import SessionManager
from ..views.provider_view import ProviderView

class ProviderController:
    """Controlador principal para operaciones con proveedores."""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self._provider_views: Dict[str, ProviderView] = {}
        
    def register_provider(self,
                         provider_id: str,
                         name: str) -> ProviderView:
        """Registra un nuevo proveedor en el sistema."""
        view = ProviderView(provider_id=provider_id, name=name)
        self._provider_views[provider_id] = view
        return view
    
    def get_provider_view(self, provider_id: str) -> Optional[ProviderView]:
        """Obtiene la vista de un proveedor."""
        return self._provider_views.get(provider_id)
    
    def update_provider_data(self,
                           provider_id: str,
                           items_data: List[dict]) -> bool:
        """
        Actualiza los datos de un proveedor.
        
        Args:
            provider_id: ID del proveedor
            items_data: Lista de diccionarios con datos de ítems
        """
        view = self._provider_views.get(provider_id)
        if not view:
            return False
            
        try:
            for item_data in items_data:
                view.add_item(
                    item_id=item_data["id"],
                    name=item_data["name"],
                    category=item_data["category"],
                    price=Decimal(str(item_data["price"]))
                )
                
                if restrictions := item_data.get("restrictions"):
                    for restriction in restrictions:
                        view.add_restriction(item_data["id"], restriction)
                        
                view.set_item_availability(
                    item_data["id"],
                    item_data.get("available", True)
                )
            return True
            
        except (KeyError, ValueError) as e:
            view.add_error(f"Error actualizando datos: {str(e)}")
            return False
    
    def get_available_items(self,
                          provider_id: str,
                          category: Optional[str] = None) -> List[dict]:
        """
        Obtiene ítems disponibles de un proveedor.
        
        Args:
            provider_id: ID del proveedor
            category: Categoría opcional para filtrar
        """
        view = self._provider_views.get(provider_id)
        if not view:
            return []
            
        items = (
            view.get_items_by_category(category)
            if category
            else view.get_available_items()
        )
        
        return [
            {
                "id": item.item_id,
                "name": item.name,
                "price": float(item.current_price),
                "category": item.category,
                "restrictions": item.restrictions,
                "price_fresh": item.is_price_fresh
            }
            for item in items
        ]
    
    def check_provider_status(self, provider_id: str) -> dict:
        """Verifica el estado de un proveedor."""
        view = self._provider_views.get(provider_id)
        if not view:
            return {"status": "not_found"}
            
        return {
            "status": view.status,
            "items_count": len(view.items),
            "errors": view.connection_errors[-5:] if view.connection_errors else []
        }
