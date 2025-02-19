"""Modelos para el manejo de presupuestos."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4


@dataclass
class BudgetItem:
    """Ítem individual del presupuesto."""

    id: str = field(default_factory=lambda: str(uuid4()))
    type: str
    description: str
    unit_price: Decimal
    quantity: int
    currency: str
    details: Dict = field(default_factory=dict)

    @property
    def total_price(self) -> Decimal:
        """Calcular precio total considerando descuentos."""
        base_total = self.unit_price * self.quantity
        discount = Decimal(str(self.details.get("discount", 0))) / 100
        return base_total * (1 - discount)


@dataclass
class Budget:
    """Presupuesto de viaje."""

    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    valid_until: datetime = None
    customer_name: Optional[str] = None
    items: List[BudgetItem] = field(default_factory=list)
    status: str = "draft"
    version: int = 1
    preferences: Dict = field(default_factory=lambda: {
        "max_budget": 0,
        "date_flexibility": "Ninguna",
        "priority": "Mejor precio",
        "additional_services": [],
        "notes": ""
    })
    adjustments_history: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        """Inicializar valores por defecto."""
        if self.valid_until is None:
            # Por defecto, válido por 7 días
            self.valid_until = datetime.now() + timedelta(days=7)

    @property
    def total_amount(self) -> Decimal:
        """Calcular monto total del presupuesto."""
        return sum(item.total_price for item in self.items)

    def add_item(self, item: BudgetItem) -> None:
        """Agregar ítem al presupuesto."""
        self.items.append(item)
        self._record_adjustment("add_item", {
            "item_id": item.id,
            "type": item.type,
            "description": item.description,
            "price": float(item.unit_price)
        })

    def update_item(self, item_id: str, **updates) -> None:
        """Actualizar un ítem existente."""
        for item in self.items:
            if item.id == item_id:
                old_values = {
                    "unit_price": float(item.unit_price),
                    "quantity": item.quantity,
                    "details": item.details.copy()
                }
                
                # Actualizar valores
                for key, value in updates.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                    elif key in item.details:
                        item.details[key] = value

                self._record_adjustment("update_item", {
                    "item_id": item_id,
                    "old_values": old_values,
                    "new_values": updates
                })
                break

    def remove_item(self, item_id: str) -> None:
        """Eliminar un ítem del presupuesto."""
        for item in self.items[:]:
            if item.id == item_id:
                self.items.remove(item)
                self._record_adjustment("remove_item", {
                    "item_id": item_id,
                    "type": item.type,
                    "description": item.description
                })
                break

    def update_preferences(self, new_preferences: Dict) -> None:
        """Actualizar preferencias del cliente."""
        old_preferences = self.preferences.copy()
        self.preferences.update(new_preferences)
        self._record_adjustment("update_preferences", {
            "old_preferences": old_preferences,
            "new_preferences": new_preferences
        })

    def _record_adjustment(self, action: str, details: Dict) -> None:
        """Registrar un ajuste en el historial."""
        self.adjustments_history.append({
            "timestamp": datetime.now(),
            "action": action,
            "details": details
        })
        self.version += 1

    def to_dict(self) -> Dict:
        """Convertir presupuesto a diccionario."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "customer_name": self.customer_name,
            "items": [
                {
                    "id": item.id,
                    "type": item.type,
                    "description": item.description,
                    "unit_price": float(item.unit_price),
                    "quantity": item.quantity,
                    "currency": item.currency,
                    "details": item.details
                }
                for item in self.items
            ],
            "status": self.status,
            "version": self.version,
            "preferences": self.preferences,
            "total_amount": float(self.total_amount),
            "adjustments_history": self.adjustments_history
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Budget':
        """Crear presupuesto desde diccionario."""
        items = [
            BudgetItem(
                id=item["id"],
                type=item["type"],
                description=item["description"],
                unit_price=Decimal(str(item["unit_price"])),
                quantity=item["quantity"],
                currency=item["currency"],
                details=item["details"]
            )
            for item in data["items"]
        ]

        return cls(
            id=data["id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            valid_until=datetime.fromisoformat(data["valid_until"]),
            customer_name=data["customer_name"],
            items=items,
            status=data["status"],
            version=data["version"],
            preferences=data["preferences"],
            adjustments_history=data.get("adjustments_history", [])
        )


def create_budget_from_package(
    package: TravelPackage,
    customer_name: str,
    passengers: Dict[str, int],
    valid_days: int = 3,
) -> Budget:
    """
    Crear un presupuesto a partir de un paquete de viaje.

    Args:
        package: Paquete de viaje
        customer_name: Nombre del cliente
        passengers: Diccionario con cantidad de pasajeros por tipo (adults, children)
        valid_days: Días de validez del presupuesto

    Returns:
        Budget: Presupuesto generado
    """
    # Generar ID único basado en timestamp y datos del paquete
    budget_id = f"BUD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{package.id}"

    # Calcular fechas
    created_at = datetime.now()
    valid_until = created_at + timedelta(days=valid_days)

    # Crear ítem de vuelo
    flight_item = BudgetItem(
        type="flight",
        description=f"Vuelo {package.origin} - {package.destination}",
        unit_price=Decimal(str(package.price)),
        quantity=sum(passengers.values()),
        currency=package.currency,
        details={
            "provider": package.provider,
            "departure_date": package.departure_date,
            "return_date": package.return_date,
            "flight_details": package.details,
        },
    )

    # Crear notas con información importante
    notes = f"""
    Presupuesto válido hasta: {valid_until.strftime('%d/%m/%Y')}
    Pasajeros: {passengers.get('adults', 0)} adultos, {passengers.get('children', 0)} niños
    Origen: {package.origin}
    Destino: {package.destination}
    Fecha ida: {package.departure_date.strftime('%d/%m/%Y %H:%M')}
    """
    if package.return_date:
        notes += f"Fecha vuelta: {package.return_date.strftime('%d/%m/%Y %H:%M')}\n"

    # Crear presupuesto
    return Budget(
        id=budget_id,
        created_at=created_at,
        valid_until=valid_until,
        customer_name=customer_name,
        items=[flight_item],
        notes=notes,
        status="draft",
    )
