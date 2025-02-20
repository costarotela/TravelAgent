"""
Clases base para proveedores de viajes.

Este módulo implementa los siguientes principios:

1. Elaboración de presupuestos:
   - Define las estructuras de datos necesarias para construir presupuestos
   - Estandariza la información de paquetes de viaje

2. Adaptación a cambios:
   - Diseño flexible que permite agregar nuevos proveedores
   - Estructura adaptable a diferentes formatos de datos

3. Datos en tiempo real:
   - Soporte para actualización de precios y disponibilidad
   - Integración con APIs de proveedores

4. Interfaz interactiva:
   - Métodos para consultar y filtrar paquetes
   - Facilita la presentación de información al usuario

5. Reconstrucción:
   - Los paquetes pueden ser serializados y reconstruidos
   - Mantiene información necesaria para recrear presupuestos
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4


@dataclass
class Flight:
    """Representa un vuelo en un paquete de viaje."""

    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    flight_number: str
    airline: str
    price: float
    passengers: int = 1
    flight_id: UUID = field(default_factory=uuid4)
    cabin_class: str = "economy"


@dataclass
class Accommodation:
    """Representa alojamiento en un paquete de viaje."""

    name: str
    location: str
    start_date: datetime
    end_date: datetime
    room_type: str
    price_per_night: float
    hotel_id: UUID = field(default_factory=uuid4)
    rating: Optional[float] = None
    amenities: List[str] = field(default_factory=list)

    @property
    def nights(self) -> int:
        """Calcula el número de noches."""
        return (self.end_date - self.start_date).days


@dataclass
class Activity:
    """Representa una actividad en un paquete de viaje."""

    name: str
    description: str
    location: str
    date: datetime
    duration: str
    price: float
    participants: int = 1
    activity_id: UUID = field(default_factory=uuid4)
    includes: List[str] = field(default_factory=list)


@dataclass
class TravelPackage:
    """Representa un paquete de viaje completo."""

    destination: str
    start_date: datetime
    end_date: datetime
    price: float
    currency: str = "USD"
    id: UUID = field(default_factory=uuid4)
    provider: Optional[str] = None
    flights: List[Flight] = field(default_factory=list)
    accommodation: Optional[Accommodation] = None
    activities: List[Activity] = field(default_factory=list)
    description: Optional[str] = None

    @property
    def duration_days(self) -> int:
        """Calcula la duración del paquete en días."""
        return (self.end_date - self.start_date).days

    @property
    def total_cost(self) -> float:
        """Calcula el costo total del paquete."""
        flight_cost = sum(f.price for f in self.flights)
        accommodation_cost = (
            self.accommodation.price_per_night * self.accommodation.nights
            if self.accommodation
            else 0
        )
        activity_cost = sum(a.price for a in self.activities)
        return flight_cost + accommodation_cost + activity_cost
