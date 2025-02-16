"""Script para probar el sistema de estimación de impacto."""
import sys
import os
from datetime import datetime, timedelta
import numpy as np

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.analysis.impact_estimator import ImpactEstimator

async def test_impact_estimator():
    """Probar el sistema de estimación de impacto."""
    print("\n=== Probando sistema de estimación de impacto ===")
    
    # Crear estimador
    estimator = ImpactEstimator()
    
    # Datos de prueba
    routes = [
        ("Buenos Aires", "Madrid"),
        ("Buenos Aires", "Barcelona"),
        ("Buenos Aires", "Roma")
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
            'prices': prices,
            'demand_score': np.random.random(),
            'seasonal_factors': {
                str(i): np.random.random() 
                for i in range(1, 13)
            },
            'competitors': [
                {'active': np.random.random() > 0.5}
                for _ in range(5)
            ]
        }
    
    # Generar datos históricos de prueba
    def generate_historical_data(success_rate, days_back, origin, destination):
        now = datetime.now()
        return [
            {
                'type': action_type,
                'origin': origin,
                'destination': destination,
                'impact': np.random.random(),
                'success': np.random.random() < success_rate,
                'date': now - timedelta(days=np.random.randint(0, days_back))
            }
            for action_type in ['purchase', 'sell', 'investigate']
            for _ in range(5)
        ]
    
    for origin, destination in routes:
        print(f"\nAnalizando ruta: {origin} -> {destination}")
        
        # Generar datos de prueba
        market_data = generate_market_data(0.1)
        historical_data = generate_historical_data(0.8, 60, origin, destination)
        
        # Probar diferentes tipos de acciones
        for action_type in ['purchase', 'sell', 'investigate']:
            print(f"\n1. Estimación para acción: {action_type}")
            
            # Estimar impacto
            estimation = await estimator.estimate_impact(
                action_type,
                origin,
                destination,
                market_data,
                historical_data
            )
            
            # Mostrar resultados
            print(f"   ✓ Impacto estimado: {estimation['estimated_impact']:.2%}")
            print(f"   ✓ Confianza: {estimation['confidence']:.2%}")
            print("\n   Condiciones de mercado:")
            print(f"   ✓ Volatilidad: {estimation['market_condition'].volatility:.2%}")
            print(f"   ✓ Tendencia: {estimation['market_condition'].trend}")
            print(f"   ✓ Demanda: {estimation['market_condition'].demand:.2%}")
            print(f"   ✓ Estacionalidad: {estimation['market_condition'].seasonality:.2%}")
            print(f"   ✓ Nivel de competencia: {estimation['market_condition'].competition_level:.2%}")
            
            if estimation['historical_impact'].sample_size > 0:
                print("\n   Datos históricos:")
                print(f"   ✓ Impacto promedio: {estimation['historical_impact'].avg_impact:.2%}")
                print(f"   ✓ Tasa de éxito: {estimation['historical_impact'].success_rate:.2%}")
                print(f"   ✓ Nivel de confianza: {estimation['historical_impact'].confidence_level:.2%}")
                print(f"   ✓ Tamaño de muestra: {estimation['historical_impact'].sample_size}")
                print(f"   ✓ Factor de recencia: {estimation['historical_impact'].recency_factor:.2%}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_impact_estimator())
