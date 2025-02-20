"""Modelos para presupuestos."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from ..schemas import TravelPackage
from ..services import PackageService


@dataclass
class BudgetItem:
    """Item de presupuesto."""

    description: str
    amount: Decimal
    quantity: int = 1
    currency: str = "USD"
    metadata: Dict = field(default_factory=dict)
    item_id: UUID = field(default_factory=uuid4)

    @property
    def total_amount(self) -> Decimal:
        """Calcula el monto total del item."""
        return self.amount * self.quantity


@dataclass
class Budget:
    """Presupuesto de viaje."""

    items: List[BudgetItem]
    currency: str = "USD"
    metadata: Dict = field(default_factory=dict)
    budget_id: UUID = field(default_factory=uuid4)

    @property
    def total_amount(self) -> Decimal:
        """Calcula el monto total del presupuesto."""
        return sum(item.total_amount for item in self.items)

    def to_dict(self) -> Dict:
        """Convierte el presupuesto a diccionario."""
        return {
            "budget_id": str(self.budget_id),
            "currency": self.currency,
            "items": [
                {
                    "item_id": str(item.item_id),
                    "description": item.description,
                    "amount": str(item.amount),
                    "quantity": item.quantity,
                    "currency": item.currency,
                    "metadata": item.metadata,
                }
                for item in self.items
            ],
            "metadata": self.metadata,
            "total_amount": str(self.total_amount),
        }


def create_budget_from_package(package: TravelPackage) -> Budget:
    """
    Crea un presupuesto a partir de un paquete de viaje.
    
    Args:
        package: Paquete de viaje
        
    Returns:
        Presupuesto creado
    """
    service = PackageService()
    items = []

    # Calcular el total de los componentes individuales
    total_components = Decimal("0")
    
    # Sumar vuelos
    flight_total = sum(flight.price * flight.passengers for flight in package.flights) if package.flights else Decimal("0")
    total_components += flight_total

    # Sumar alojamiento
    accommodation_total = (package.accommodation.price_per_night * package.accommodation.nights) if package.accommodation else Decimal("0")
    total_components += accommodation_total

    # Sumar actividades incluidas
    activities_total = sum(activity.price * activity.participants for activity in package.activities if activity.included) if package.activities else Decimal("0")
    total_components += activities_total

    # Calcular factor de ajuste para distribuir el precio total
    adjustment_factor = package.total_price / total_components if total_components > 0 else Decimal("1")

    # Agregar vuelos ajustados
    if package.flights:
        for flight in package.flights:
            items.append(
                BudgetItem(
                    description=f"Vuelo {flight.flight_number}: {flight.origin}-{flight.destination}",
                    amount=Decimal(str(flight.price)) * adjustment_factor,
                    quantity=flight.passengers,
                    currency=package.currency,
                    metadata={
                        "departure_time": flight.departure_time.isoformat(),
                        "arrival_time": flight.arrival_time.isoformat(),
                        "airline": flight.airline
                    }
                )
            )

    # Agregar alojamiento ajustado
    if package.accommodation:
        items.append(
            BudgetItem(
                description=f"Alojamiento en {package.accommodation.name}",
                amount=Decimal(str(package.accommodation.price_per_night)) * adjustment_factor,
                quantity=package.accommodation.nights,
                currency=package.currency,
                metadata={
                    "hotel_id": package.accommodation.hotel_id,
                    "room_type": package.accommodation.room_type,
                    "check_in": package.accommodation.check_in.isoformat(),
                    "check_out": package.accommodation.check_out.isoformat()
                }
            )
        )

    # Agregar actividades ajustadas
    if package.activities:
        for activity in package.activities:
            if activity.included:
                items.append(
                    BudgetItem(
                        description=f"Actividad: {activity.name}",
                        amount=Decimal(str(activity.price)) * adjustment_factor,
                        quantity=activity.participants,
                        currency=package.currency,
                        metadata={
                            "activity_id": activity.activity_id,
                            "duration": str(activity.duration),
                            "date": activity.date.isoformat()
                        }
                    )
                )

    return Budget(
        items=items,
        currency=package.currency,
        metadata={
            "package_id": str(package.id),
            "provider": package.provider,
            "destination": package.destination,
            "start_date": package.start_date.isoformat(),
            "end_date": package.end_date.isoformat(),
            "total_price": str(service.calculate_total_price(package))
        }
    )
