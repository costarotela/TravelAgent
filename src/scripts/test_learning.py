"""Script para probar el sistema de aprendizaje."""

import sys
import os
from datetime import datetime

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.agent.execution import execution_system
from src.core.agent.learning import learning_system


async def test_learning():
    """Probar el sistema de aprendizaje."""
    print("\n=== Probando sistema de aprendizaje ===")

    routes = [
        ("Buenos Aires", "Madrid"),
        ("Buenos Aires", "Barcelona"),
        ("Buenos Aires", "Roma"),
    ]

    for origin, destination in routes:
        print(f"\nAnalizando ruta: {origin} -> {destination}")

        # 1. Ejecutar plan
        result, executions = await execution_system.execute_plan(origin, destination)

        # 2. Aprender de la ejecución
        print("\n1. Métricas de Aprendizaje:")
        metrics = await learning_system.learn_from_execution(
            (origin, destination), executions
        )
        print(f"   ✓ Precisión: {metrics.accuracy:.2%}")
        print(f"   ✓ Error de impacto: {metrics.impact_error:.2%}")
        print(f"   ✓ Calibración de confianza: {metrics.confidence_calibration:.2%}")
        print(f"   ✓ Tasa de éxito: {metrics.execution_success_rate:.2%}")
        print(f"   ✓ Tiempo promedio: {metrics.avg_execution_time:.2f}s")
        print(f"   ✓ Tasa de mejora: {metrics.improvement_rate:.2%}")

        # 3. Obtener recomendaciones
        print("\n2. Recomendaciones:")
        recommendations = await learning_system.get_route_recommendations(
            origin, destination
        )

        if recommendations.get("best_actions"):
            print("\n   Mejores Acciones:")
            for action in recommendations["best_actions"]:
                print(f"   ✓ {action['action_type']}:")
                print(f"     - Tasa de éxito: {action['stats']['success_rate']:.2%}")
                print(f"     - Impacto promedio: {action['stats']['avg_impact']:.2%}")
                print(f"     - Tendencia: {action['stats']['trend']}")

        if recommendations.get("improvement_opportunities"):
            print("\n   Oportunidades de Mejora:")
            for improvement in recommendations["improvement_opportunities"]:
                print(f"   ➜ {improvement['type']}:")
                print(f"     - Recomendación: {improvement['recommendation']}")

        print(
            f"\n   Ajuste de confianza: {recommendations.get('confidence_adjustments', 0.0):.2%}"
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_learning())
