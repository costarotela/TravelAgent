"""Script para probar el sistema de planificación."""

import sys
import os
from datetime import datetime

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.agent.planning import planning_system


async def test_planning():
    """Probar el sistema de planificación."""
    print("\n=== Probando sistema de planificación ===")

    routes = [
        ("Buenos Aires", "Madrid"),
        ("Buenos Aires", "Barcelona"),
        ("Buenos Aires", "Roma"),
    ]

    for origin, destination in routes:
        print(f"\nGenerando plan para ruta: {origin} -> {destination}")
        plan = await planning_system.create_plan(origin, destination)

        if plan:
            print(f"\n1. Estado del Mercado:")
            print(f"   ✓ Estado: {plan.market_status}")
            print(f"   ✓ Riesgo: {plan.risk_level}")
            print(f"   ✓ Confianza: {plan.confidence:.2%}")

            print(f"\n2. Acciones Recomendadas:")
            for i, action in enumerate(plan.actions, 1):
                print(f"\n   Acción {i}:")
                print(f"   ✓ Tipo: {action.type.value}")
                print(f"   ✓ Prioridad: {action.priority.value}")
                print(f"   ✓ Descripción: {action.description}")
                print(f"   ✓ Impacto esperado: {action.expected_impact:.1f}%")
                print(f"   ✓ Deadline: {action.deadline.strftime('%Y-%m-%d %H:%M')}")

            print(f"\n3. Métricas:")
            print(f"   ✓ Beneficio estimado: {plan.estimated_profit:.2f}%")
            print(f"   ✓ Válido hasta: {plan.valid_until.strftime('%Y-%m-%d %H:%M')}")

            print(f"\n4. Metadata:")
            print(f"   ✓ Tendencia precios: {plan.metadata['price_trend']}")
            print(f"   ✓ Tendencia demanda: {plan.metadata['demand_trend']}")
            print(f"   ✓ Volatilidad: {plan.metadata['volatility']:.2f}%")
            print(f"   ✓ Precio promedio: ${plan.metadata['avg_price']:.2f}")
        else:
            print("✗ No hay datos suficientes para generar un plan")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_planning())
