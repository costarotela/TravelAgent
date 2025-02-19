# Integración con OLA.com.ar

## Principios de Integración

### 1. Estabilidad Durante la Sesión
La integración con OLA.com.ar sigue el principio fundamental de estabilidad durante las sesiones de venta:
- Los datos se capturan al inicio de la sesión
- No se realizan actualizaciones durante la interacción vendedor-cliente
- Las validaciones se posponen hasta el cierre de la sesión

### 2. Control del Vendedor
El vendedor mantiene control total sobre el proceso:
- Control explícito sobre modificaciones
- Decisiones informadas sobre cambios
- Gestión completa de la interacción

### 3. Procesamiento Asíncrono
Las actualizaciones y validaciones se manejan de forma asíncrona:
- Los cambios se detectan fuera de las sesiones activas
- Las notificaciones se almacenan para futuras sesiones
- La consistencia se mantiene durante toda la interacción

## Componentes Principales

### 1. SessionBudgetManager ✅ (IMPRESCINDIBLE)
- Manejo de sesiones de presupuesto
- Control de estado durante la venta
- Aislamiento de datos por sesión
```python
session = SessionBudgetManager(
    storage_manager,
    event_emitter
)
```

### 2. OlaScraper ✅ (IMPRESCINDIBLE)
- Extracción inicial de datos
- Captura de información completa
- Validaciones básicas de datos
```python
scraper = OlaScraper(
    session_manager,
    cache_manager
)
```

### 3. ChangeDetector ⚠️ (PARCIALMENTE NECESARIO)
- Detección asíncrona de cambios
- Procesamiento fuera de sesión
- Notificaciones para futuras interacciones
```python
detector = ChangeDetector()
# Solo se ejecuta fuera de sesiones activas
changes = await detector.detect_changes_async(old_package, new_package)
```

## Flujo de Trabajo

### 1. Inicio de Sesión de Venta
```python
# 1. Crear sesión de presupuesto
session_id = await session_manager.create_session(vendor_id, customer_id)

# 2. Capturar datos iniciales
initial_data = await scraper.get_package_data(package_id)
await session_manager.add_package_to_session(session_id, initial_data)
```

### 2. Durante la Sesión
```python
# Los datos permanecen estables
session_data = await session_manager.get_session_data(session_id)

# Modificaciones controladas por el vendedor
await session_manager.modify_package_in_session(
    session_id,
    package_id,
    vendor_modifications
)
```

### 3. Cierre de Sesión
```python
# 1. Finalizar sesión y crear presupuesto
budget = await session_manager.finalize_session(session_id)

# 2. Validar cambios (asíncrono)
asyncio.create_task(detector.validate_changes_after_session(budget))
```

## Consideraciones de Implementación

### Prioridades
1. ✅ IMPRESCINDIBLE
   - SessionBudgetManager
   - Extracción básica de datos
   - Validaciones esenciales

2. ⚠️ PARCIALMENTE NECESARIO
   - Detección de cambios asíncrona
   - Sistema de notificaciones
   - Caché de datos frecuentes

3. ❌ OMITIBLE
   - Validaciones en tiempo real
   - Optimizaciones de rendimiento
   - Análisis predictivo

### Métricas de Éxito
1. Tiempo de creación de sesión < 2 segundos
2. Tiempo de respuesta en modificaciones < 1 segundo
3. Zero interrupciones durante sesión activa
4. 100% consistencia de datos durante la sesión

## Modelos de Datos

```python
class PaqueteOLA:
    destino: str
    aerolinea: str
    origen: str
    duracion: int
    moneda: str
    incluye: List[str]
    fechas: List[str]
    precio: float
    impuestos: float
    politicas_cancelacion: PoliticasCancelacion
    vuelos: List[VueloDetallado]
```

## Seguridad y Rendimiento

### Medidas Anti-bloqueo
1. Rotación de User Agents
2. Delays dinámicos entre requests
3. Sistema de reintentos con backoff exponencial
4. Headers realistas para simular navegador

### Manejo de Errores
1. Detección de errores de login
2. Reintentos automáticos en caso de fallos
3. Logging detallado para debugging

## Uso del Scraper

### Configuración
```python
config = ScraperConfig(
    base_url="https://ola.com.ar",
    login_required=True,
    headless=True,
    credentials=Credentials(
        username="your_username",
        password="your_password"
    )
)
```

### Ejemplo de Uso
```python
async with OlaScraper(config) as scraper:
    # Login automático
    if await scraper.login():
        # Búsqueda de paquetes
        packages = await scraper.search_packages({
            "destino": "Costa Mujeres",
            "fechas": ["2025-03-02", "2025-03-25"]
        })
```

## Componentes Omitidos ❌

Los siguientes componentes se han omitido intencionalmente para mantener el enfoque en funcionalidades críticas:

1. Sistema de caché complejo
   - Razón: No crítico para la extracción en tiempo real
   - Consideración futura: Implementar si el rendimiento se vuelve problema

2. Sistema de alertas avanzado
   - Razón: La versión simple actual cubre necesidades básicas
   - Consideración futura: Expandir basado en feedback de usuarios

3. Optimizaciones de rendimiento
   - Razón: El rendimiento actual es suficiente
   - Consideración futura: Optimizar basado en métricas de uso

## Pruebas

El sistema incluye pruebas automatizadas para:
1. Manejo de sesiones y anti-bloqueo
2. Detección de cambios en paquetes
3. Funcionalidad de login y scraping

Para ejecutar las pruebas:
```bash
python -m pytest tests/test_ola_scraper.py -v
```

## Mantenimiento

### Logs y Monitoreo
- Los logs incluyen información detallada de:
  - Intentos de login
  - Cambios detectados en paquetes
  - Errores y reintentos
  - Rotación de User Agents

### Actualizaciones Necesarias
1. Mantener lista de User Agents actualizada
2. Revisar selectores CSS periódicamente
3. Actualizar umbrales de cambios significativos según necesidad
