"""Módulo de presupuestos."""

from datetime import datetime, timedelta
from typing import Dict, Any
from decimal import Decimal

from src.core.budget.models import Budget, BudgetItem
from src.core.providers.base import TravelPackage


def create_budget_from_package(
    package: TravelPackage,
    customer_name: str,
    passengers: Dict[str, int],
    valid_days: int = 3,
) -> Budget:
    """Crear un presupuesto a partir de un paquete."""
    # Crear item del presupuesto
    budget_item = BudgetItem(
        description=f"{package.origin} → {package.destination}",
        unit_price=Decimal(str(package.price)),
        quantity=sum(passengers.values()),
        currency=package.currency,
        details={
            "departure_date": (
                package.departure_date.isoformat() if package.departure_date else None
            ),
            "return_date": (
                package.return_date.isoformat() if package.return_date else None
            ),
            "provider": package.provider,
            "package_id": package.id,
            **package.details,
            **passengers,
        },
    )

    # Crear presupuesto
    budget = Budget(
        id="",  # Se generará automáticamente
        items=[budget_item],
        customer_name=customer_name,
        created_at=datetime.now(),
        valid_until=datetime.now() + timedelta(days=valid_days),
        status="draft",
    )

    return budget


__all__ = ["Budget", "BudgetItem", "create_budget_from_package"]
