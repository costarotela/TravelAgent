"""Script para probar el sistema de calibración de confianza."""
import sys
import os
from datetime import datetime, timedelta
import numpy as np

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.analysis.confidence_calibrator import ConfidenceCalibrator

async def test_confidence_calibrator():
    """Probar el sistema de calibración de confianza."""
    print("\n=== Probando sistema de calibración de confianza ===")
    
    # Crear calibrador
    calibrator = ConfidenceCalibrator()
    
    # Datos de prueba
    action_types = ['purchase', 'sell', 'investigate']
    
    # Generar datos históricos sintéticos
    def generate_historical_data(num_samples: int = 50):
        data = []
        now = datetime.now()
        
        for _ in range(num_samples):
            # Generar confianza predicha
            confidence = np.random.random()
            
            # Simular resultado basado en confianza
            # Más probable que sea exitoso si la confianza es alta
            success = np.random.random() < (0.5 + confidence * 0.3)
            
            data.append({
                'type': np.random.choice(action_types),
                'confidence': confidence,
                'success': success,
                'date': now - timedelta(days=np.random.randint(0, 30))
            })
            
        return data
    
    # Generar condiciones de mercado
    market_conditions = {
        'volatility': 0.15,
        'trend': 'stable',
        'demand': 0.7
    }
    
    # Probar calibración para diferentes niveles de confianza
    confidence_levels = [0.3, 0.5, 0.7, 0.9]
    historical_data = generate_historical_data()
    
    for action_type in action_types:
        print(f"\nCalibrando confianza para acción: {action_type}")
        
        for confidence in confidence_levels:
            print(f"\n1. Nivel de confianza original: {confidence:.2%}")
            
            # Calibrar confianza
            calibrated, metrics = await calibrator.calibrate_confidence(
                confidence,
                action_type,
                market_conditions,
                historical_data
            )
            
            # Mostrar resultados
            print(f"   ✓ Confianza calibrada: {calibrated:.2%}")
            print("\n   Métricas de calibración:")
            print(f"   ✓ Score de calibración: {metrics.calibration_score:.2%}")
            print(f"   ✓ Confiabilidad: {metrics.reliability_score:.2%}")
            print(f"   ✓ Precisión: {metrics.sharpness_score:.2%}")
            print(f"   ✓ Resolución: {metrics.resolution_score:.2%}")
            print(f"   ✓ Incertidumbre: {metrics.uncertainty:.2%}")
            
            # Simular resultado y actualizar calibración
            actual_outcome = float(np.random.random() < calibrated)
            calibrator.update_calibration(
                confidence,
                actual_outcome,
                action_type
            )
    
    # Mostrar estadísticas finales
    print("\nEstadísticas globales de calibración:")
    stats = calibrator.get_calibration_stats()
    
    if stats:
        print(f"✓ Confianza media predicha: {stats['mean_predicted']:.2%}")
        print(f"✓ Resultado medio real: {stats['mean_actual']:.2%}")
        print(f"✓ Correlación: {stats['correlation']:.2%}")
        print(f"✓ Número de muestras: {stats['num_samples']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_confidence_calibrator())
