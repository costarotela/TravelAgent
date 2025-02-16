"""Script para probar el sistema de análisis."""
import sys
import os
from datetime import datetime, timedelta

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.agent.analysis import analysis_system

async def test_analysis():
    """Probar el sistema de análisis."""
    print("\n=== Probando sistema de análisis ===")
    
    routes = [
        ("Buenos Aires", "Madrid"),
        ("Buenos Aires", "Barcelona"),
        ("Buenos Aires", "Roma")
    ]
    
    for origin, destination in routes:
        print(f"\nAnalizando ruta: {origin} -> {destination}")
        insight = await analysis_system.analyze_route(origin, destination)
        
        if insight:
            print(f"\n1. Tendencias:")
            print(f"   ✓ Precios: {insight.price_trend}")
            print(f"   ✓ Volatilidad: {insight.price_volatility:.2f}%")
            print(f"   ✓ Demanda: {insight.demand_trend}")
            print(f"   ✓ Estacionalidad: {insight.seasonality}")
            
            print(f"\n2. Datos de soporte:")
            print(f"   ✓ Precio promedio: ${insight.supporting_data['avg_price']:.2f}")
            print(f"   ✓ Rango de precios: ${insight.supporting_data['price_range']:.2f}")
            print(f"   ✓ Disponibilidad promedio: {insight.supporting_data['avg_availability']:.1f}")
            
            print(f"\n3. Recomendación:")
            print(f"   ➜ {insight.recommendation.upper()}")
            print(f"   ✓ Confianza: {insight.confidence:.2%}")
        else:
            print("✗ No hay datos suficientes")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_analysis())
