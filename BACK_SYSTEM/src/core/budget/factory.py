"""Factory functions for creating budgets."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional

from src.core.providers.base import TravelPackage
from .models import Budget, BudgetItem


def create_budget_from_package(
    package: TravelPackage,
    customer_name: Optional[str] = None,
    passengers: Optional[Dict[str, int]] = None,
    valid_days: int = 7
) -> Budget:
    """
    Crear un presupuesto a partir de un paquete de viaje.
    
    Args:
        package: Paquete de viaje
        customer_name: Nombre del cliente (opcional)
        passengers: Diccionario con cantidad de pasajeros por tipo (opcional)
        valid_days: Días de validez del presupuesto
    
    Returns:
        Budget: Presupuesto generado
    """
    if passengers is None:
        passengers = {"adults": 1}

    # Crear ítem de vuelo
    flight_item = BudgetItem(
        type="flight",
        description=f"{package.origin} - {package.destination}",
        unit_price=Decimal(str(package.price)),
        quantity=sum(passengers.values()),
        currency=package.currency,
        details={
            "flight_details": {
                "flight_number": package.details.get("flight_number"),
                "airline": package.details.get("airline"),
                "cabin_class": package.details.get("cabin_class", "Economy"),
                "baggage": package.details.get("baggage", "23kg")
            },
            "departure_date": package.departure_date,
            "return_date": package.return_date,
            "passengers": passengers
        }
    )

    # Crear presupuesto
    budget = Budget(
        customer_name=customer_name,
        items=[flight_item],
        valid_until=datetime.now() + timedelta(days=valid_days)
    )

    return budget
