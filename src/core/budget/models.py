"""Módulo para la generación y manejo de presupuestos."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from ..providers.base import TravelPackage

@dataclass
class BudgetItem:
    """Ítem individual de un presupuesto."""
    type: str  # 'flight', 'hotel', 'transfer', etc.
    description: str
    unit_price: Decimal
    quantity: int
    currency: str
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "type": self.type,
            "description": self.description,
            "unit_price": str(self.unit_price),
            "quantity": self.quantity,
            "currency": self.currency,
            "details": {
                k: v.isoformat() if isinstance(v, (datetime)) else v
                for k, v in self.details.items()
            }
        }

    @property
    def total_price(self) -> Decimal:
        """Calcular precio total del ítem."""
        return self.unit_price * self.quantity

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BudgetItem':
        """Crear desde diccionario."""
        return cls(
            type=data["type"],
            description=data["description"],
            unit_price=Decimal(data["unit_price"]),
            quantity=data["quantity"],
            currency=data["currency"],
            details=data["details"]
        )

@dataclass
class Budget:
    """Presupuesto completo."""
    id: str
    created_at: datetime
    valid_until: datetime
    customer_name: str
    items: List[BudgetItem]
    notes: Optional[str] = None
    status: str = "draft"  # draft, sent, accepted, rejected
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "customer_name": self.customer_name,
            "items": [item.to_dict() for item in self.items],
            "notes": self.notes,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Budget':
        """Crear desde diccionario."""
        return cls(
            id=data["id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            valid_until=datetime.fromisoformat(data["valid_until"]),
            customer_name=data["customer_name"],
            items=[BudgetItem.from_dict(item) for item in data["items"]],
            notes=data.get("notes"),
            status=data.get("status", "draft")
        )

    @property
    def total_amount(self) -> Dict[str, Decimal]:
        """Calcular monto total por moneda."""
        totals = {}
        for item in self.items:
            if item.currency not in totals:
                totals[item.currency] = Decimal('0')
            totals[item.currency] += item.total_price
        return totals

def create_budget_from_package(
    package: TravelPackage,
    customer_name: str,
    passengers: Dict[str, int],
    valid_days: int = 3
) -> Budget:
    """Crear un presupuesto a partir de un paquete de viaje."""
    now = datetime.now()
    valid_until = now.replace(hour=23, minute=59, second=59) + timedelta(days=valid_days)
    
    # Calcular cantidad total de pasajeros
    total_passengers = sum(passengers.values())
    
    # Crear ítem de vuelo
    flight_item = BudgetItem(
        type=package.type,  # Usar el tipo del paquete
        description=f"Vuelo {package.origin} → {package.destination}",
        unit_price=Decimal(str(package.price)),
        quantity=total_passengers,
        currency=package.currency,
        details={
            "flight_number": package.details.get("flight_number"),
            "airline": package.details.get("airline"),
            "departure_date": package.departure_date,
            "return_date": package.return_date,
            "cabin_class": package.details.get("cabin_class"),
            "baggage": package.details.get("baggage"),
            "passengers": passengers,
            "type": package.details.get("type", "direct")  # Tipo específico de vuelo
        }
    )
    
    # Crear presupuesto
    budget = Budget(
        id=f"BUD-{now.strftime('%Y%m%d')}-{package.id}",
        created_at=now,
        valid_until=valid_until,
        customer_name=customer_name,
        items=[flight_item],
        notes=f"""
        Presupuesto válido hasta: {valid_until.strftime('%d/%m/%Y %H:%M')}
        Incluye:
        - Vuelo en {package.details.get('airline')}
        - Clase: {package.details.get('cabin_class')}
        - Equipaje: {package.details.get('baggage')}
        """.strip()
    )
    
    return budget
