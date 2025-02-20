"""
Servicio para la reconstrucción de presupuestos.
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional
from uuid import UUID

from ..views.budget_view import BudgetView
from ..views.provider_view import ProviderView
from .models import BudgetSnapshot, PriceHistory, ReconstructionData

class ReconstructionService:
    """Servicio principal para reconstrucción de presupuestos."""
    
    def __init__(self):
        self._reconstructions: Dict[UUID, ReconstructionData] = {}
    
    def create_snapshot(self,
                       budget_view: BudgetView,
                       metadata: Optional[Dict[str, str]] = None) -> BudgetSnapshot:
        """
        Crea una captura del estado actual de un presupuesto.
        
        Args:
            budget_view: Vista del presupuesto a capturar
            metadata: Metadatos opcionales
        """
        snapshot = BudgetSnapshot(
            budget_id=budget_view.session.session.current_budget_id,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        for item_id, item in budget_view._items.items():
            snapshot.add_item(
                item_id=item_id,
                provider_id=item.provider_id,
                price=item.current_price,
                quantity=item.quantity,
                description=item.description
            )
        
        return snapshot
    
    def store_reconstruction_data(self,
                                snapshot: BudgetSnapshot,
                                provider_views: Dict[str, ProviderView]) -> UUID:
        """
        Almacena datos para futura reconstrucción.
        
        Args:
            snapshot: Captura del presupuesto
            provider_views: Vistas de proveedores involucrados
        """
        recon_data = ReconstructionData(original_snapshot=snapshot)
        
        # Almacena historial de precios
        for item_id, item in snapshot.items.items():
            provider_id = item["provider_id"]
            if provider := provider_views.get(provider_id):
                if provider_item := provider.items.get(item_id):
                    history = PriceHistory(
                        item_id=item_id,
                        provider_id=provider_id
                    )
                    history.add_price(
                        provider_item.current_price,
                        provider_item.last_update
                    )
                    recon_data.add_price_history(history)
        
        # Almacena estado de proveedores
        for provider_id, provider in provider_views.items():
            recon_data.set_provider_state(provider_id, {
                "status": provider.status,
                "items_count": len(provider.items),
                "last_error": provider.connection_errors[-1] if provider.connection_errors else None
            })
        
        self._reconstructions[snapshot.budget_id] = recon_data
        return snapshot.budget_id
    
    def reconstruct_budget(self,
                          budget_id: UUID,
                          target_time: Optional[datetime] = None) -> Optional[BudgetSnapshot]:
        """
        Reconstruye un presupuesto con datos históricos.
        
        Args:
            budget_id: ID del presupuesto a reconstruir
            target_time: Momento específico para la reconstrucción
        """
        recon_data = self._reconstructions.get(budget_id)
        if not recon_data:
            return None
            
        target_time = target_time or datetime.now()
        original = recon_data.original_snapshot
        
        # Crea nueva captura con precios actualizados
        new_snapshot = BudgetSnapshot(
            budget_id=original.budget_id,
            timestamp=target_time,
            metadata={
                **original.metadata,
                "reconstructed_from": original.timestamp.isoformat()
            }
        )
        
        for item_id, item in original.items.items():
            new_price = recon_data.get_item_price(item_id, target_time)
            if new_price is None:
                new_price = item["price"]  # Usa precio original si no hay historial
                
            new_snapshot.add_item(
                item_id=item_id,
                provider_id=item["provider_id"],
                price=new_price,
                quantity=item["quantity"],
                **{k: v for k, v in item.items() if k not in ["provider_id", "price", "quantity"]}
            )
        
        return new_snapshot
