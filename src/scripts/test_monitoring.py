"""Script para probar el sistema de monitoreo."""

import random
import time
from datetime import datetime, timedelta

from src.utils.monitoring import monitor


def simulate_searches():
    """Simular búsquedas con diferentes resultados."""
    providers = ["AERO", "OLA", "DESPEGAR"]

    for _ in range(10):
        # Simular tiempo de búsqueda
        duration = random.uniform(0.5, 3.0)
        monitor.log_metric("search_duration", duration)

        # Simular resultados por proveedor
        for provider in providers:
            # Simular éxito/error
            if random.random() > 0.2:  # 80% de éxito
                results = random.randint(5, 20)
                monitor.log_metric(
                    "search_success", 1, {"provider": provider, "results": results}
                )
                # Simular cache hit
                if random.random() > 0.7:  # 30% de cache hit
                    monitor.log_metric("cache_hit", 1, {"provider": provider})
            else:
                # Simular error
                error = Exception("Error de conexión simulado")
                monitor.log_error(error, {"provider": provider, "action": "search"})
                monitor.log_metric("provider_errors", 1, {"provider": provider})

        # Simular resultados totales
        total_results = random.randint(15, 60)
        monitor.log_metric("total_results", total_results)

        # Esperar un poco
        time.sleep(0.5)


def main():
    """Ejecutar prueba del sistema de monitoreo."""
    print("Iniciando prueba del sistema de monitoreo...")
    print("Simulando búsquedas...")

    simulate_searches()

    print("Prueba completada. Verifica el dashboard de monitoreo.")


if __name__ == "__main__":
    main()
