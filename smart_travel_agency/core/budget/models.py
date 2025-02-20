"""
Modelos básicos para el manejo de presupuestos.

Este módulo implementa los siguientes principios:

1. Elaboración de presupuestos:
   - Define las estructuras de datos fundamentales para representar presupuestos
   - Permite la construcción dinámica de presupuestos a partir de paquetes de viaje

2. Adaptación a cambios:
   - Los modelos son flexibles y pueden adaptarse a diferentes tipos de items
   - Soporta múltiples monedas y tipos de servicios

3. Datos en tiempo real:
   - Los modelos pueden actualizarse con información en tiempo real
   - Mantiene registro de cambios y actualizaciones

4. Interfaz interactiva:
   - Proporciona métodos para manipular y consultar presupuestos
   - Facilita la interacción con la interfaz de usuario

5. Reconstrucción:
   - Los modelos pueden ser serializados y reconstruidos
   - Mantiene un historial de cambios para reconstrucción
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Union
from uuid import UUID, uuid4

from smart_travel_agency.core.schemas import TravelPackage


class BudgetItem:
    """Representa un ítem individual en un presupuesto."""

    def __init__(
        self,
        type: str,
        description: str,
        unit_price: Decimal,
        quantity: int = 1,
        currency: str = "USD",
        item_id: Optional[UUID] = None,
        metadata: Optional[Dict] = None,
    ):
        """
        Inicializa un nuevo ítem de presupuesto.

        Args:
            type: Tipo de ítem (vuelo, hotel, etc.)
            description: Descripción detallada
            unit_price: Precio unitario
            quantity: Cantidad de unidades
            currency: Moneda (default: USD)
            item_id: Identificador único (opcional)
            metadata: Datos adicionales (opcional)
        """
        self.type = type
        self.description = description
        self.unit_price = unit_price
        self.quantity = quantity
        self.currency = currency
        self.item_id = item_id or uuid4()
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.updated_at = self.created_at

    @property
    def total_price(self) -> Decimal:
        """Calcula el precio total del ítem."""
        return self.unit_price * self.quantity

    def update(self, **kwargs) -> None:
        """
        Actualiza los atributos del ítem.

        Args:
            **kwargs: Pares clave-valor de atributos a actualizar
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()


class Budget:
    """Representa un presupuesto completo."""

    def __init__(
        self,
        items: Optional[List[BudgetItem]] = None,
        currency: str = "USD",
        budget_id: Optional[UUID] = None,
        metadata: Optional[Dict] = None,
    ):
        """
        Inicializa un nuevo presupuesto.

        Args:
            items: Lista de ítems del presupuesto
            currency: Moneda base del presupuesto
            budget_id: Identificador único
            metadata: Datos adicionales
        """
        self.items = items or []
        self.currency = currency
        self.budget_id = budget_id or uuid4()
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.updated_at = self.created_at
        self._history = []

    def add_item(self, item: BudgetItem) -> None:
        """
        Agrega un ítem al presupuesto.

        Args:
            item: Ítem a agregar
        """
        self.items.append(item)
        self._record_change("add_item", item)
        self.updated_at = datetime.now()

    def remove_item(self, item_id: UUID) -> Optional[BudgetItem]:
        """
        Elimina un ítem del presupuesto.

        Args:
            item_id: ID del ítem a eliminar

        Returns:
            El ítem eliminado o None si no se encontró
        """
        for i, item in enumerate(self.items):
            if item.item_id == item_id:
                removed = self.items.pop(i)
                self._record_change("remove_item", removed)
                self.updated_at = datetime.now()
                return removed
        return None

    def update_item(self, item_id: UUID, **kwargs) -> bool:
        """
        Actualiza un ítem existente.

        Args:
            item_id: ID del ítem a actualizar
            **kwargs: Atributos a actualizar

        Returns:
            True si se actualizó el ítem, False si no se encontró
        """
        for item in self.items:
            if item.item_id == item_id:
                old_state = {k: getattr(item, k) for k in kwargs.keys()}
                item.update(**kwargs)
                self._record_change("update_item", item, old_state=old_state)
                self.updated_at = datetime.now()
                return True
        return False

    @property
    def total(self) -> Decimal:
        """Calcula el total del presupuesto."""
        return sum(item.total_price for item in self.items)

    def _record_change(
        self, action: str, item: BudgetItem, old_state: Optional[Dict] = None
    ) -> None:
        """
        Registra un cambio en el historial.

        Args:
            action: Tipo de acción realizada
            item: Ítem afectado
            old_state: Estado anterior (para actualizaciones)
        """
        self._history.append({
            "action": action,
            "item_id": item.item_id,
            "timestamp": datetime.now(),
            "old_state": old_state,
        })


def create_budget_from_package(package: TravelPackage) -> Budget:
    """
    Crea un presupuesto a partir de un paquete de viaje.

    Args:
        package: Paquete de viaje

    Returns:
        Un nuevo presupuesto basado en el paquete
    """
    budget = Budget(
        currency=package.currency,
        metadata={
            "package_id": package.package_id,
            "provider": package.provider,
            "destination": package.destination,
        }
    )

    # Agregar vuelos
    if package.flights:
        for flight in package.flights:
            budget.add_item(BudgetItem(
                type="flight",
                description=f"{flight.origin} -> {flight.destination}",
                unit_price=Decimal(str(flight.price)),
                quantity=flight.passengers,
                currency=package.currency,
                metadata={
                    "flight_number": flight.flight_number,
                    "departure": flight.departure_time,
                    "arrival": flight.arrival_time,
                }
            ))

    # Agregar alojamiento
    if package.accommodation:
        budget.add_item(BudgetItem(
            type="accommodation",
            description=package.accommodation.name,
            unit_price=Decimal(str(package.accommodation.price_per_night)),
            quantity=package.accommodation.nights,
            currency=package.currency,
            metadata={
                "hotel_id": package.accommodation.hotel_id,
                "room_type": package.accommodation.room_type,
                "check_in": package.accommodation.check_in,
                "check_out": package.accommodation.check_out,
            }
        ))

    # Agregar actividades
    if package.activities:
        for activity in package.activities:
            budget.add_item(BudgetItem(
                type="activity",
                description=activity.name,
                unit_price=Decimal(str(activity.price)),
                quantity=activity.participants,
                currency=package.currency,
                metadata={
                    "activity_id": activity.activity_id,
                    "duration": activity.duration,
                    "date": activity.date,
                }
            ))

    return budget
