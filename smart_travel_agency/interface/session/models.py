"""
Modelos para el Gestor de Sesiones de la Interfaz de Vendedor.

Este módulo define las estructuras de datos necesarias para mantener
el estado de una sesión de vendedor durante la elaboración de presupuestos.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

@dataclass
class VendorSession:
    """Representa una sesión activa de vendedor."""
    
    id: UUID = field(default_factory=uuid4)
    start_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    # Datos del vendedor
    vendor_id: str
    vendor_name: str
    
    # Estado actual del presupuesto
    current_budget_id: Optional[UUID] = None
    modified_items: Dict[str, dict] = field(default_factory=dict)
    pending_updates: List[dict] = field(default_factory=list)
    
    def update_activity(self) -> None:
        """Actualiza el timestamp de última actividad."""
        self.last_activity = datetime.now()
    
    def start_budget_edit(self, budget_id: UUID) -> None:
        """Inicia la edición de un presupuesto."""
        self.current_budget_id = budget_id
        self.modified_items.clear()
        self.pending_updates.clear()
        self.update_activity()
    
    def add_modification(self, item_id: str, changes: dict) -> None:
        """Registra una modificación al presupuesto actual."""
        if not self.current_budget_id:
            raise ValueError("No hay un presupuesto activo en edición")
        
        self.modified_items[item_id] = changes
        self.update_activity()
    
    def queue_update(self, update_data: dict) -> None:
        """Agrega una actualización pendiente para procesar después."""
        self.pending_updates.append(update_data)
        self.update_activity()
    
    def close(self) -> None:
        """Cierra la sesión actual."""
        self.is_active = False
        self.current_budget_id = None
        self.modified_items.clear()
        self.pending_updates.clear()

@dataclass
class SessionState:
    """Estado completo de una sesión incluyendo datos de proveedores."""
    
    session: VendorSession
    provider_data: Dict[str, dict] = field(default_factory=dict)
    cached_prices: Dict[str, float] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    
    def update_provider_data(self, provider_id: str, data: dict) -> None:
        """Actualiza datos de un proveedor en la sesión."""
        self.provider_data[provider_id] = data
        self.session.update_activity()
    
    def cache_price(self, item_id: str, price: float) -> None:
        """Cachea un precio para uso durante la sesión."""
        self.cached_prices[item_id] = price
        self.session.update_activity()
    
    def add_validation_error(self, error: str) -> None:
        """Agrega un error de validación."""
        self.validation_errors.append(error)
        self.session.update_activity()
    
    def clear_validation_errors(self) -> None:
        """Limpia los errores de validación."""
        self.validation_errors.clear()
        self.session.update_activity()
