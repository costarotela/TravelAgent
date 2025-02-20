# SmartTravelAgency 

Sistema inteligente para agencias de viajes que facilita la creación, gestión y optimización de presupuestos de viaje.

## Objetivos Principales

1. **Elaboración Dinámica de Presupuestos**
   - Integración con múltiples proveedores
   - Optimización automática de precios
   - Sistema flexible de preferencias

2. **Procesamiento en Tiempo Real**
   - Web scraping inteligente
   - Integración con APIs de proveedores
   - Actualización dinámica de precios

3. **Adaptabilidad**
   - Configuración flexible de proveedores
   - Sistema de preferencias multinivel
   - Reglas de negocio personalizables

4. **Control del Vendedor**
   - Interfaz interactiva
   - Gestión de preferencias personalizadas
   - Historial y métricas de éxito

## Arquitectura

### Core
```
smart_travel_agency/
├── core/
│   ├── providers/           # Integración con proveedores
│   │   ├── scrapers/       # Web scrapers específicos
│   │   │   ├── ola_scraper.py
│   │   │   └── aero_scraper.py
│   │   ├── manager.py      # Gestión de proveedores
│   │   └── config.py       # Configuración de scrapers
│   ├── analysis/
│   │   └── price_optimizer/ # Optimización de precios
│   ├── budget/             # Gestión de presupuestos
│   ├── vendors/            # Gestión de vendedores
│   │   └── preferences.py  # Sistema de preferencias
│   └── services/           # Servicios principales
│       └── package_service.py
```

## Componentes Principales

### 1. Sistema de Proveedores
- **ProviderIntegrationManager**: Coordina búsquedas entre proveedores
- **Scrapers**: Implementaciones específicas para cada proveedor
  - OlaScraper
  - AeroScraper
- **Configuración**: Sistema flexible para configurar cada scraper

### 2. Optimización de Precios
- **PriceOptimizer**: Optimiza precios basado en:
  - Factores de mercado
  - Demanda y estacionalidad
  - Competencia
  - Calidad del servicio

### 3. Sistema de Preferencias
- **Nivel Base**: Preferencias estándar de proveedores
  - Aerolíneas preferidas
  - Ratings mínimos
  - Tipos de habitación
  
- **Nivel Negocio**: Reglas de la empresa
  - Márgenes y comisiones
  - Perfiles de cliente
  - Ajustes estacionales
  
- **Nivel Vendedor**: Preferencias personalizadas
  - Combinaciones exitosas
  - Notas y observaciones
  - Métricas de rendimiento

### 4. Gestión de Paquetes
- **PackageService**: Servicio principal que:
  - Integra proveedores y optimización
  - Valida y construye paquetes
  - Aplica preferencias y reglas

## Uso

### Configuración de Proveedores
```python
from smart_travel_agency.core.services import PackageService

service = PackageService.get_instance()
await service.initialize_providers({
    "ola": {
        "username": "user1",
        "password": "pass1"
    },
    "aero": {
        "username": "user2",
        "password": "pass2"
    }
})
```

### Búsqueda y Optimización
```python
result = await service.search_and_optimize_packages(
    destination="MIA",
    start_date=datetime.now() + timedelta(days=30),
    end_date=datetime.now() + timedelta(days=37),
    adults=2,
    children=1
)
```

### Gestión de Preferencias
```python
from smart_travel_agency.core.vendors.preferences import (
    PreferenceManager, VendorPreferences, BasePreferences
)

manager = PreferenceManager()

# Configurar preferencias de vendedor
preferences = VendorPreferences(
    vendor_id="V001",
    name="Juan Pérez",
    base=BasePreferences(
        preferred_airlines=["LATAM", "AA"],
        min_rating=4.0
    )
)

manager.update_vendor_preferences(preferences)
```

## Métricas y Monitoreo

- **Éxito de Búsquedas**: Tasa de éxito por proveedor
- **Optimización**: Mejora en márgenes
- **Rendimiento**: Tiempos de respuesta
- **Vendedores**: Métricas por vendedor

## Seguridad

- Credenciales en variables de entorno
- Rotación de User-Agents
- Rate limiting configurable
- Validación de datos

## Desarrollo

### Requisitos
- Python 3.8+
- aiohttp
- BeautifulSoup4
- Prometheus client

### Instalación
```bash
pip install -r requirements.txt
```

### Tests
```bash
pytest tests/
```

## Notas de Implementación

1. **Scrapers**
   - Implementar manejo de errores robusto
   - Considerar caché para optimizar rendimiento
   - Mantener configuración flexible

2. **Optimización**
   - Refinar algoritmos de pricing
   - Implementar más factores de mercado
   - Mejorar predicciones de demanda

3. **Preferencias**
   - Expandir perfiles de cliente
   - Agregar más reglas de negocio
   - Mejorar sistema de reconstrucción

## Contribución

1. Fork el repositorio
2. Crea una rama (`git checkout -b feature/mejora`)
3. Commit tus cambios (`git commit -am 'Agrega mejora'`)
4. Push a la rama (`git push origin feature/mejora`)
5. Crea un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.
