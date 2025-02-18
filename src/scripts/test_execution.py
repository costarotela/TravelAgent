"""Script para probar el sistema de ejecución."""

import sys
import os
from datetime import datetime

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.agent.execution import execution_system, ExecutionResult


async def test_execution():
    """Probar el sistema de ejecución."""
    print("\n=== Probando sistema de ejecución ===")

    routes = [
        ("Buenos Aires", "Madrid"),
        ("Buenos Aires", "Barcelona"),
        ("Buenos Aires", "Roma"),
    ]

    for origin, destination in routes:
        print(f"\nEjecutando plan para ruta: {origin} -> {destination}")
        result, executions = await execution_system.execute_plan(origin, destination)

        print(f"\n1. Resultado General:")
        print(f"   ✓ Estado: {result.value}")

        print(f"\n2. Ejecuciones:")
        for i, execution in enumerate(executions, 1):
            print(f"\n   Ejecución {i}:")
            print(f"   ✓ Tipo: {execution.action.type.value}")
            print(f"   ✓ Estado: {execution.status.value}")
            print(
                f"   ✓ Resultado: {execution.result.value if execution.result else 'N/A'}"
            )
            print(
                f"   ✓ Impacto: {execution.impact:.2f}% si está disponible"
                if execution.impact
                else "   ✗ Impacto: No disponible"
            )
            print(
                f"   ✓ Duración: {(execution.end_time - execution.start_time).total_seconds():.2f}s"
            )

            if execution.error:
                print(f"   ✗ Error: {execution.error}")

            print(f"\n   Metadata:")
            print(f"   ✓ Estado mercado: {execution.metadata['market_status']}")
            print(f"   ✓ Nivel riesgo: {execution.metadata['risk_level']}")
            print(f"   ✓ Confianza: {execution.metadata['confidence']:.2%}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_execution())
