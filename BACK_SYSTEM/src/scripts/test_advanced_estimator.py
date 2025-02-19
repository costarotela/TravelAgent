"""Script para probar el sistema integrado de estimación."""

import sys
import os
from datetime import datetime, timedelta
import numpy as np
from tabulate import tabulate

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.analysis.advanced_estimator import AdvancedEstimator


async def test_advanced_estimator():
    """Probar el sistema integrado de estimación."""
    print("\n=== Probando sistema integrado de estimación ===")

    # Crear estimador
    estimator = AdvancedEstimator()

    # Datos de prueba
    routes = [
        ("Buenos Aires", "Madrid"),
        ("Buenos Aires", "Barcelona"),
        ("Buenos Aires", "Roma"),
    ]

    # Generar datos de mercado de prueba
    def generate_market_data(volatility_factor):
        base_price = 1000
        days = 30
        prices = []

        for i in range(days):
            noise = np.random.normal(0, volatility_factor * base_price)
            price = base_price + noise
            prices.append(max(0, price))

        return {
            "prices": prices,
            "demand_score": np.random.random(),
            "seasonal_factors": {str(i): np.random.random() for i in range(1, 13)},
            "competitors": [{"active": np.random.random() > 0.5} for _ in range(5)],
            "volatility": volatility_factor,
        }

    # Generar datos históricos de prueba
    def generate_historical_data(success_rate, days_back, origin, destination):
        now = datetime.now()
        return [
            {
                "type": action_type,
                "origin": origin,
                "destination": destination,
                "impact": np.random.random(),
                "success": np.random.random() < success_rate,
                "confidence": np.random.random(),
                "date": now - timedelta(days=np.random.randint(0, days_back)),
            }
            for action_type in ["purchase", "sell", "investigate"]
            for _ in range(5)
        ]

    # Tabla para resultados
    results = []

    for origin, destination in routes:
        print(f"\nAnalizando ruta: {origin} -> {destination}")

        # Generar datos de prueba con diferentes niveles de volatilidad
        volatility = np.random.uniform(0.1, 0.3)
        market_data = generate_market_data(volatility)
        historical_data = generate_historical_data(0.8, 60, origin, destination)

        # Probar diferentes tipos de acciones
        for action_type in ["purchase", "sell", "investigate"]:
            print(f"\n1. Análisis para acción: {action_type}")

            # Realizar análisis
            estimation = await estimator.analyze(
                action_type, origin, destination, market_data, historical_data
            )

            # Agregar a resultados
            results.append(
                [
                    f"{origin} -> {destination}",
                    action_type,
                    f"{estimation.estimated_impact:.2%}",
                    f"{estimation.raw_confidence:.2%}",
                    f"{estimation.calibrated_confidence:.2%}",
                    f"{estimation.market_condition.volatility:.2%}",
                    estimation.recommendation,
                    estimation.risk_level,
                ]
            )

            # Mostrar resultados detallados
            print(f"   ✓ Impacto estimado: {estimation.estimated_impact:.2%}")
            print(f"   ✓ Confianza original: {estimation.raw_confidence:.2%}")
            print(f"   ✓ Confianza calibrada: {estimation.calibrated_confidence:.2%}")
            print(f"   ✓ Recomendación: {estimation.recommendation}")
            print(f"   ✓ Nivel de riesgo: {estimation.risk_level}")

            print("\n   Condiciones de mercado:")
            print(f"   ✓ Volatilidad: {estimation.market_condition.volatility:.2%}")
            print(f"   ✓ Tendencia: {estimation.market_condition.trend}")
            print(f"   ✓ Demanda: {estimation.market_condition.demand:.2%}")

            print("\n   Métricas de calibración:")
            print(f"   ✓ Score: {estimation.calibration_metrics.calibration_score:.2%}")
            print(
                f"   ✓ Confiabilidad: {estimation.calibration_metrics.reliability_score:.2%}"
            )
            print(
                f"   ✓ Resolución: {estimation.calibration_metrics.resolution_score:.2%}"
            )

    # Mostrar tabla de resultados
    print("\nResumen de Análisis:")
    headers = [
        "Ruta",
        "Acción",
        "Impacto",
        "Conf. Original",
        "Conf. Calibrada",
        "Volatilidad",
        "Recomendación",
        "Riesgo",
    ]
    print(tabulate(results, headers=headers, tablefmt="grid"))


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_advanced_estimator())
