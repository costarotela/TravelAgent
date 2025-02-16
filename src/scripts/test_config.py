"""Script para probar la configuración básica."""
import sys
import os
from datetime import datetime

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.config.settings import settings
from src.core.database.base import db
from src.core.models.travel import TravelPackage
from src.core.cache.redis_cache import cache

async def test_configuration():
    """Probar la configuración básica del sistema."""
    print("\n=== Prueba de Configuración ===")
    
    # 1. Probar configuración
    print("\n1. Configuración cargada:")
    print(f"Database URL: {settings.DATABASE_URL}")
    print(f"Redis Host: {settings.REDIS_HOST}")
    print(f"Cache TTL: {settings.CACHE_TTL}")
    
    # 2. Probar base de datos
    print("\n2. Prueba de base de datos:")
    try:
        with db.get_session() as session:
            # Crear un paquete de prueba
            test_package = TravelPackage(
                provider_id="TEST",
                origin="Buenos Aires",
                destination="Madrid",
                departure_date=datetime.now(),
                price=1000.0,
                currency="USD",
                availability=10,
                details={"test": True}
            )
            session.add(test_package)
            session.commit()  # Commit explícito
            print("✓ Inserción en base de datos exitosa")
            
            # Consultar el paquete
            package = session.query(TravelPackage).filter_by(provider_id="TEST").first()
            if package:
                print(f"✓ Consulta exitosa: {package.origin} -> {package.destination}")
            else:
                print("✗ No se encontró el paquete")
    except Exception as e:
        print(f"✗ Error en base de datos: {e}")
    
    # 3. Probar caché
    print("\n3. Prueba de caché:")
    try:
        # Guardar en caché
        await cache.set("test_key", {"status": "ok"})
        print("✓ Escritura en caché exitosa")
        
        # Leer de caché
        value = await cache.get("test_key")
        print(f"✓ Lectura de caché exitosa: {value}")
    except Exception as e:
        print(f"✗ Error en caché: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_configuration())
