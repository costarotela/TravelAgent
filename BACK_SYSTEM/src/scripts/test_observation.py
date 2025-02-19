"""Script para probar el sistema de observación."""

import sys
import os
from datetime import datetime, timedelta
import random

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.database.base import db
from src.core.models.travel import TravelPackage
from src.core.agent.observation import observation_system


async def generate_test_data():
    """Generar datos de prueba."""
    print("\n=== Generando datos de prueba ===")

    routes = [
        ("Buenos Aires", "Madrid"),
        ("Buenos Aires", "Barcelona"),
        ("Buenos Aires", "Roma"),
    ]

    with db.get_session() as session:
        # Generar datos para los últimos 30 días
        for days_ago in range(30):
            date = datetime.utcnow() - timedelta(days=days_ago)

            for origin, destination in routes:
                # Simular tendencia de precios
                base_price = 1000.0
                if origin == "Buenos Aires" and destination == "Madrid":
                    # Tendencia al alza
                    trend_factor = 1.0 + (days_ago / 100)
                elif origin == "Buenos Aires" and destination == "Barcelona":
                    # Tendencia a la baja
                    trend_factor = 1.0 - (days_ago / 150)
                else:
                    # Estable con variación aleatoria
                    trend_factor = 1.0 + random.uniform(-0.1, 0.1)

                price = base_price * trend_factor

                package = TravelPackage(
                    provider_id=f"TEST-{random.randint(1000, 9999)}",
                    origin=origin,
                    destination=destination,
                    departure_date=date + timedelta(days=30),
                    price=price,
                    currency="USD",
                    availability=random.randint(0, 100),
                    details={"test": True},
                    created_at=date,
                )
                session.add(package)

        session.commit()
        print("✓ Datos de prueba generados")


async def test_observation():
    """Probar el sistema de observación."""
    print("\n=== Probando sistema de observación ===")

    routes = [
        ("Buenos Aires", "Madrid"),
        ("Buenos Aires", "Barcelona"),
        ("Buenos Aires", "Roma"),
    ]

    for origin, destination in routes:
        print(f"\nAnalizando ruta: {origin} -> {destination}")
        trend = await observation_system.observe_route(origin, destination)

        if trend:
            print(f"✓ Tendencia: {trend.trend}")
            print(f"✓ Precio promedio: ${trend.avg_price:.2f}")
            print(f"✓ Demanda: {trend.demand_score:.2%}")
            print(f"✓ Confianza: {trend.confidence:.2%}")
        else:
            print("✗ No hay datos suficientes")


if __name__ == "__main__":
    import asyncio

    async def main():
        await generate_test_data()
        await test_observation()

    asyncio.run(main())
