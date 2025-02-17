"""Proveedor de vuelos simulado para desarrollo."""
from datetime import datetime, timedelta
import random
from typing import List, Dict, Any
import asyncio

from .base import TravelProvider, TravelPackage, SearchCriteria

class AeroProvider(TravelProvider):
    """Proveedor de vuelos simulado."""

    def __init__(self, config: Dict[str, Any]):
        """Inicializar proveedor."""
        super().__init__(config)
        self.name = config.get("name", "aero")

    async def search_packages(self, criteria: SearchCriteria) -> List[TravelPackage]:
        """Buscar paquetes de viaje."""
        # Simular tiempo de búsqueda
        await asyncio.sleep(1)

        # Generar vuelos simulados
        results = []

        # Vuelo directo (el más barato)
        results.append(TravelPackage(
            id=f"vuelo_directo_{random.randint(1000, 9999)}",
            provider="aero",
            type="flight",
            origin=criteria.origin,
            destination=criteria.destination,
            departure_date=criteria.departure_date,
            return_date=criteria.return_date,
            price=random.uniform(800, 1200),
            currency="USD",
            details={
                "airline": "Aerolíneas Test",
                "flight_number": f"TEST{random.randint(100, 999)}",
                "baggage": "23kg",
                "cabin_class": "Economy",
                "type": "direct",
                "duration": "2h 30m"
            }
        ))
        
        # Vuelo con escala (precio medio)
        results.append(TravelPackage(
            id=f"vuelo_escala_{random.randint(1000, 9999)}",
            provider="aero",
            type="flight",
            origin=criteria.origin,
            destination=criteria.destination,
            departure_date=criteria.departure_date,
            return_date=criteria.return_date,
            price=random.uniform(600, 900),
            currency="USD",
            details={
                "airline": "Low Cost Airways",
                "flight_number": f"LOW{random.randint(100, 999)}",
                "baggage": "10kg",
                "cabin_class": "Economy",
                "type": "stopover",
                "duration": "4h 30m",
                "stops": ["Paris"]
            }
        ))
        
        # Vuelo premium (el más caro)
        results.append(TravelPackage(
            id=f"vuelo_premium_{random.randint(1000, 9999)}",
            provider="aero",
            type="flight",
            origin=criteria.origin,
            destination=criteria.destination,
            departure_date=criteria.departure_date,
            return_date=criteria.return_date,
            price=random.uniform(1500, 2000),
            currency="USD",
            details={
                "airline": "Premium Airlines",
                "flight_number": f"PRE{random.randint(100, 999)}",
                "baggage": "32kg",
                "cabin_class": "Business",
                "type": "premium",
                "duration": "2h 30m",
                "lounge_access": True
            }
        ))
        
        return results

    async def get_package_details(self, package_id: str) -> TravelPackage:
        """Obtener detalles de un paquete."""
        # Simular búsqueda del paquete
        await asyncio.sleep(0.5)
        
        # Generar un paquete de ejemplo basado en el ID
        return TravelPackage(
            id=package_id,
            provider="aero",
            type="flight",
            origin="Buenos Aires",
            destination="Madrid",
            departure_date=datetime.now().date(),
            return_date=None,
            price=random.uniform(800, 2000),
            currency="USD",
            details={
                "airline": "Aerolíneas Test",
                "flight_number": f"TEST{random.randint(100, 999)}",
                "baggage": "23kg",
                "cabin_class": "Economy",
                "type": "direct",
                "duration": "2h 30m"
            }
        )

    async def check_availability(self, package_id: str) -> bool:
        """Verificar disponibilidad de un paquete."""
        # Simular verificación
        await asyncio.sleep(0.5)
        return random.choice([True, True, True, False])  # 75% de probabilidad de disponibilidad
