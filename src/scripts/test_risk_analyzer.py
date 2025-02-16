"""Script para probar el sistema de análisis de riesgo."""
import sys
import os
from datetime import datetime, timedelta
import numpy as np
from tabulate import tabulate

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.analysis.risk_analyzer import RiskAnalyzer

async def test_risk_analyzer():
    """Probar el sistema de análisis de riesgo."""
    print("\n=== Probando sistema de análisis de riesgo ===")
    
    # Crear analizador
    analyzer = RiskAnalyzer()
    
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
        demand = []
        
        # Generar precios con tendencia y volatilidad
        trend = np.random.choice([-1, 1])
        for i in range(days):
            trend_component = trend * i * base_price * 0.001
            noise = np.random.normal(0, volatility_factor * base_price)
            price = base_price + trend_component + noise
            prices.append(max(0, price))
            
            # Generar demanda correlacionada negativamente con precio
            demand_noise = np.random.normal(0, 0.1)
            demand_value = 1.0 - (price - base_price) / base_price + demand_noise
            demand.append(max(0, min(1, demand_value)))
        
        return {
            'prices': prices,
            'demand': demand,
            'demand_score': np.mean(demand),
            'seasonal_factors': {
                str(i): np.random.random() 
                for i in range(1, 13)
            },
            'competitors': [
                {
                    'active': np.random.random() > 0.5,
                    'market_share': np.random.random() * 0.2
                }
                for _ in range(5)
            ],
            'volatility': volatility_factor
        }
    
    # Generar datos financieros de prueba
    def generate_financial_data(operational_complexity):
        return {
            'operational_complexity': operational_complexity,
            'financial_exposure': np.random.random() * 0.5,
            'liquidity_ratio': 1.5 + np.random.random(),
            'debt_ratio': 0.3 + np.random.random() * 0.3,
            'profit_margin': 0.15 + np.random.random() * 0.1
        }
    
    # Generar datos históricos de prueba
    def generate_historical_data(success_rate, days_back, origin, destination):
        now = datetime.now()
        data = []
        
        for _ in range(50):
            impact = np.random.random()
            expected_impact = impact + np.random.normal(0, 0.1)
            
            data.append({
                'type': np.random.choice(['purchase', 'sell', 'investigate']),
                'origin': origin,
                'destination': destination,
                'impact': impact,
                'expected_impact': expected_impact,
                'success': np.random.random() < success_rate,
                'demand': 0.5 + np.random.random() * 0.5,
                'date': now - timedelta(days=np.random.randint(0, days_back))
            })
            
        return data
    
    # Tabla para resultados
    results = []
    
    for origin, destination in routes:
        print(f"\nAnalizando ruta: {origin} -> {destination}")
        
        # Generar datos de prueba con diferentes niveles de riesgo
        volatility = np.random.uniform(0.1, 0.3)
        market_data = generate_market_data(volatility)
        
        operational_complexity = np.random.uniform(0.3, 0.7)
        financial_data = generate_financial_data(operational_complexity)
        
        historical_data = generate_historical_data(0.8, 60, origin, destination)
        
        # Probar diferentes tipos de acciones
        for action_type in ['purchase', 'sell', 'investigate']:
            print(f"\n1. Análisis para acción: {action_type}")
            
            # Realizar análisis de riesgo
            metrics, risk_level, recommendations = await analyzer.analyze_risk(
                action_type,
                market_data,
                financial_data,
                historical_data
            )
            
            # Agregar a resultados
            results.append([
                f"{origin} -> {destination}",
                action_type,
                f"{metrics.total_risk:.2%}",
                risk_level,
                f"{metrics.var_95:.2%}",
                f"{metrics.risk_tolerance:.2%}",
                f"{metrics.risk_capacity:.2%}"
            ])
            
            # Mostrar resultados detallados
            print(f"   ✓ Riesgo total: {metrics.total_risk:.2%}")
            print(f"   ✓ Nivel de riesgo: {risk_level}")
            print("\n   Componentes de riesgo:")
            print(f"   ✓ Riesgo de mercado: {metrics.market_risk:.2%}")
            print(f"   ✓ Riesgo operacional: {metrics.operational_risk:.2%}")
            print(f"   ✓ Riesgo financiero: {metrics.financial_risk:.2%}")
            
            print("\n   Métricas de riesgo:")
            print(f"   ✓ VaR (95%): {metrics.var_95:.2%}")
            print(f"   ✓ CVaR (95%): {metrics.cvar_95:.2%}")
            print(f"   ✓ Tolerancia: {metrics.risk_tolerance:.2%}")
            print(f"   ✓ Capacidad: {metrics.risk_capacity:.2%}")
            
            print("\n   Recomendaciones:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
            
            # Simular resultado y actualizar histórico
            actual_outcome = float(np.random.random() < (1 - metrics.total_risk))
            analyzer.update_risk_history(
                action_type,
                metrics,
                actual_outcome
            )
    
    # Mostrar tabla de resultados
    print("\nResumen de Análisis de Riesgo:")
    headers = [
        "Ruta", "Acción", "Riesgo Total", "Nivel",
        "VaR (95%)", "Tolerancia", "Capacidad"
    ]
    print(tabulate(results, headers=headers, tablefmt="grid"))
    
    # Mostrar estadísticas finales
    print("\nEstadísticas globales de riesgo:")
    stats = analyzer.get_risk_stats()
    
    if stats:
        print(f"✓ Riesgo medio: {stats['mean_risk']:.2%}")
        print(f"✓ Volatilidad del riesgo: {stats['risk_volatility']:.2%}")
        print(f"✓ Tendencia del riesgo: {stats['risk_trend']}")
        print(f"✓ Número de muestras: {stats['num_samples']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_risk_analyzer())
