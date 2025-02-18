# Arquitectura del Sistema

## Objetivo Principal
El SmartTravelAgent tiene un único propósito central: **la elaboración dinámica de presupuestos de viaje con asistencia al vendedor**.

## Estructura Core

### 1. Módulo de Presupuestos (`src/core/budget/`)
El corazón del sistema, enfocado en la creación y gestión de presupuestos.

#### Components Clave:
- `budget_engine/`: Motor de construcción de presupuestos
- `price_tracker.py`: Seguimiento simple de precios
  ```python
  # Ejemplo de uso:
  price_tracker.track_price(package)  # Registra precio actual
  history = price_tracker.get_price_history(package_id)  # Obtiene historial básico
  ```
- `rules.py`: Reglas básicas para presupuestos
  ```python
  # Ejemplo de uso:
  rules.apply_margin(price, client_type)  # Aplica margen según tipo de cliente
  rules.validate_budget_items(items)  # Validación básica
  ```

### 2. Extracción de Datos (`src/core/collectors/` y `src/core/browsers/`)
Enfocado en obtener datos actualizados de proveedores.

- `collectors/`: Recolección de datos de APIs
- `browsers/`: Web scraping cuando sea necesario

### 3. Integración con Proveedores (`src/core/providers/`)
Conexión directa con proveedores de servicios.

### 4. Interfaz del Vendedor
Herramientas para que el vendedor interactúe con el sistema.

## Alineación con Objetivos

1. **Elaboración de Presupuestos**
   - ✓ `budget_engine/`: Construcción de presupuestos
   - ✓ `rules.py`: Reglas de negocio simples
   - ✓ `price_tracker.py`: Seguimiento de precios

2. **Construcción Dinámica con Asistencia**
   - ✓ Interfaz interactiva para el vendedor
   - ✓ Validación en tiempo real
   - ✓ Sugerencias basadas en disponibilidad

3. **Adaptación a Cambios**
   - ✓ Actualización continua de precios
   - ✓ Seguimiento de disponibilidad
   - ✓ Caché para rendimiento

4. **Extracción de Datos en Tiempo Real**
   - ✓ Collectors para APIs
   - ✓ Browsers para web scraping
   - ✓ Sistema de caché

5. **Interfaz del Vendedor**
   - ✓ Dashboard interactivo
   - ✓ Validación inmediata
   - ✓ Sugerencias de optimización

6. **Reconstrucción de Presupuestos**
   - ✓ Versionamiento de presupuestos
   - ✓ Historial de cambios
   - ✓ Comparación de versiones

## Reglas de Desarrollo

1. **Mantener la Simplicidad**
   - Evitar análisis complejos innecesarios
   - Enfocarse en la funcionalidad esencial
   - Priorizar la experiencia del vendedor

2. **Enfoque en Presupuestos**
   - Cada función debe contribuir a la creación de presupuestos
   - Evitar funcionalidades que no apoyen este objetivo
   - Mantener el foco en la asistencia al vendedor

3. **Datos Actualizados**
   - Priorizar la actualización de precios y disponibilidad
   - Usar caché de manera efectiva
   - Mantener tiempos de respuesta rápidos

4. **Experiencia del Vendedor**
   - Interfaz intuitiva
   - Respuestas rápidas
   - Validación en tiempo real

## NO Incluido en el Alcance

Para evitar desviaciones, estos elementos NO son parte del sistema:
- ❌ Análisis complejo de mercado
- ❌ Predicciones avanzadas de precios
- ❌ Análisis de comportamiento de proveedores
- ❌ Sistemas complejos de reglas de negocio
- ❌ Análisis de riesgo avanzado

## Mantenimiento del Enfoque

Antes de agregar nueva funcionalidad, preguntar:
1. ¿Ayuda directamente en la creación de presupuestos?
2. ¿Mejora la experiencia del vendedor?
3. ¿Es necesario para la actualización de datos?

Si la respuesta es NO a todas, probablemente está fuera del alcance.
