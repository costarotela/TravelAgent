# Integración con OLA.com.ar

## Arquitectura del Scraper

### Componentes Principales

1. **SessionManager** ✅ (IMPRESCINDIBLE)
   - Manejo de sesiones HTTP
   - Rotación de User Agents
   - Sistema anti-bloqueo con backoff exponencial
   - Delays inteligentes entre requests
   ```python
   session_manager = SessionManager(
       min_delay=2.0,
       max_delay=5.0,
       max_retries=3
   )
   ```

2. **ChangeDetector** ⚠️ (PARCIALMENTE NECESARIO)
   - Detección de cambios críticos en paquetes
   - Enfoque en cambios de precio y disponibilidad
   - Análisis de significancia de cambios
   ```python
   detector = ChangeDetector()
   changes = detector.detect_changes(old_package, new_package)
   if detector.is_significant_change(changes):
       # Notificar cambios importantes
   ```

3. **OlaScraper** ✅ (IMPRESCINDIBLE)
   - Login seguro con manejo de errores
   - Extracción de datos estructurada
   - Integración con SessionManager y ChangeDetector

### Modelos de Datos

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
