# SmartTravelAgency - Guía de Desarrollo 

## Estado del Proyecto

### Componentes Implementados 

1. **Sistema de Reconstrucción de Presupuestos**
   - Estrategias: PRESERVE_MARGIN, PRESERVE_PRICE, ADJUST_PROPORTIONALLY, BEST_ALTERNATIVE
   - Análisis de impacto
   - Sistema de métricas
   - Logging detallado

2. **Integración con Proveedores**
   - ProviderIntegrationManager implementado
   - Soporte para múltiples proveedores
   - Monitoreo en tiempo real
   - Detección de cambios

3. **Optimización de Precios**
   - PriceOptimizer implementado
   - Análisis de competencia
   - Ajustes por demanda y estacionalidad
   - Cálculo de precios óptimos

4. **Manejo de Preferencias**
   - Sistema de tres niveles: Base, Negocio, Vendedor
   - Perfiles de cliente
   - Reglas de precio
   - Combinaciones exitosas

### Componentes IMPRESCINDIBLES y su Estado

### 1. Motor de Presupuestos 
Necesario para objetivo #1 y #2
- Modelos base implementados
- Cálculos básicos
- Sistema de construcción dinámica (builder.py)
   - Patrón Builder implementado
   - Validaciones en tiempo real
   - Integración con preferencias
   - Control de estados
   - Tests unitarios completos
      * Validaciones básicas
      * Preferencias del vendedor
      * Construcción de presupuestos
      * Control de estado
      * Manejo de errores
- Sistema de validación (validator.py)
   - Validaciones de integridad
   - Reglas de negocio
   - Validaciones de composición
   - Restricciones del vendedor
   - Tests unitarios completos
- Flujo completo de aprobación

### 2. Control del Vendedor 
Necesario para objetivo #2
- Sistema de preferencias implementado
- Integración con construcción (via builder.py)
- Validaciones de control (via validator.py)
- Flujo de aprobación

### 3. Sistema de Adaptación 
Necesario para objetivo #3 y #6
- Estrategias de reconstrucción
- Análisis de impacto
- Sistema de métricas
- Logging y trazabilidad

### 4. Integración con Proveedores 
Necesario para objetivo #1
- ProviderManager implementado
- Optimización de precios
- Detección de cambios
- Manejo de errores

### En Desarrollo 

1. **Sistema de Construcción de Presupuestos** ()
   - [x] Estructura básica
   - [x] Construcción dinámica basada en preferencias
   - [x] Integración con sistema de preferencias
   - [x] Validaciones avanzadas
   - [x] Tests unitarios completos
   - [x] Sistema de sugerencias durante construcción

### Próximos Pasos 

1. **Fase 1: Sistema de Construcción** (Sprint Actual)
   - [x] Implementar validaciones críticas
   - [x] Integrar con builder.py
   - [x] Agregar tests de validación
   - [x] Desarrollar sistema de sugerencias

2. **Fase 2: Mejoras de UX**
   - [x] Dashboard para visualización
   - [ ] Mejoras en la visualización de sugerencias
   - [ ] Sistema de notificaciones
   - [ ] Filtros y búsqueda avanzada

3. **Fase 3: Optimizaciones**
   - [ ] Caché para reconstrucciones
   - [ ] Mejoras en algoritmo BEST_ALTERNATIVE
   - [ ] Optimización de consultas a proveedores
   - [ ] Sistema de fallback

## Principios de Diseño 

1. **Estabilidad en Sesión de Venta**
   - Datos estables durante la sesión
   - Sin interrupciones por actualizaciones
   - Control total del vendedor

2. **Adaptabilidad**
   - Reconstrucción inteligente
   - Múltiples estrategias
   - Manejo de casos extremos

3. **Datos en Tiempo Real**
   - Integración con proveedores
   - Caché inteligente
   - Validación de datos

4. **UX Enfocada en Vendedor**
   - Feedback claro
   - Notificaciones relevantes
   - Control total del proceso

## Estructura del Proyecto 

```
SmartTravelAgency/
├── smart_travel_agency/
│   ├── core/
│   │   ├── budget/       # Motor de presupuestos
│   │   │   ├── builder.py    # 
│   │   │   ├── models.py     # 
│   │   │   ├── validator.py  # 
│   │   │   └── approval.py   # 
│   │   ├── providers/    # Integración proveedores
│   │   ├── analysis/     # Análisis y optimización
│   │   └── vendors/      # Preferencias y perfiles
│   └── interface/        # Interfaces de usuario
├── tests/                # Tests unitarios/integración
└── docs/                # Documentación
```

## Notas de Implementación 

1. **Prioridades**
   - Enfoque en componentes IMPRESCINDIBLES
   - Versión mínima de componentes PARCIALMENTE NECESARIOS
   - Documentar componentes OMITIBLES

2. **Testing**
   - Tests unitarios completos
   - Tests de integración para flujos críticos
   - Cobertura mínima: 80%

3. **Documentación**
   - Documentar alineación con principios
   - Mantener ejemplos actualizados
   - Guías de contribución

## Documentación de Sistemas

Para una descripción detallada de cada sistema y su funcionamiento, consultar [SYSTEMS.md](SYSTEMS.md).

## Historial de Cambios 

### 2025-02-20
- Documento inicial creado
- Estado actual del proyecto documentado
- Próximos pasos definidos

### 2025-02-25
- Actualización: Enfoque en componentes IMPRESCINDIBLES
- Reorganización de prioridades
- Estado actual del motor de presupuestos

### 2025-03-01
- Implementación del sistema de construcción de presupuestos (builder.py)
- Características implementadas:
  * Construcción dinámica con patrón Builder
  * Validaciones en tiempo real
  * Integración con preferencias del vendedor
  * Sistema de estados
  * Métricas Prometheus
  * Tests unitarios completos
- Actualización de documentación

### 2025-03-05
- Implementación del sistema de validación (validator.py)
- Características implementadas:
  * Validaciones de integridad
  * Reglas de negocio
  * Validaciones de composición
  * Restricciones del vendedor
  * Métricas Prometheus
  * Tests unitarios completos
- Actualización de documentación

### 2025-03-10
- Implementación del flujo de aprobación (approval.py)
- Características implementadas:
  * Estados y transiciones del workflow
  * Roles y permisos
  * Validaciones de transiciones
  * Registro de cambios y auditoría
  * Métricas Prometheus
  * Tests unitarios completos
- Actualización de documentación

### 2025-02-21
-  Completadas pruebas exhaustivas del BudgetBuilder
  * Validaciones básicas funcionando
  * Integración con preferencias verificada
  * Manejo de errores robusto
  * Control de estado validado
-  Próximo foco: Sistema de sugerencias durante construcción

## Dashboard de Presupuestos

El dashboard de presupuestos proporciona una interfaz visual para la gestión y visualización de presupuestos.

### Características

1. **Vista de Resumen**
   - Estado actual del presupuesto
   - Contador de items
   - Alertas y advertencias
   - Sugerencias de optimización

2. **Gestión de Items**
   - Lista detallada de items
   - Vista expandible con detalles
   - Metadata y propiedades
   - Información de precios y cantidades

3. **Formulario de Ingreso**
   - Interfaz intuitiva para agregar items
   - Validación de datos en tiempo real
   - Campos para metadata relevante
   - Feedback inmediato

### Uso

Para ejecutar el dashboard:

```bash
# Desde el directorio raíz del proyecto
PYTHONPATH=/home/pablo/CascadeProjects/SmartTravelAgency streamlit run smart_travel_agency/ui/dashboard/budget_dashboard.py
```

### Estructura

```
smart_travel_agency/
└── ui/
    └── dashboard/
        ├── __init__.py
        └── budget_dashboard.py
```

## Sistema de Sugerencias

El `BudgetBuilder` incluye un sistema de sugerencias inteligente que ayuda a optimizar los presupuestos. Las sugerencias se generan automáticamente en base a diferentes criterios:

### Tipos de Sugerencias

1. **Optimización de Costos**
   - Detecta items que exceden los montos máximos definidos en las preferencias del vendedor
   - Sugiere alternativas más económicas manteniendo la calidad del servicio
   - Considera el historial de precios y las preferencias del cliente

2. **Optimización por Temporada**
   - Identifica servicios en temporada alta
   - Sugiere fechas alternativas para obtener mejores tarifas
   - Ayuda a distribuir servicios en temporadas más convenientes

3. **Optimización de Paquetes**
   - Detecta múltiples servicios del mismo proveedor
   - Sugiere la contratación de paquetes para obtener mejores precios
   - Agrupa servicios relacionados para maximizar descuentos

### Implementación

- Las sugerencias se generan automáticamente al agregar cada item
- Se mantiene un historial de sugerencias accesible vía `get_suggestions()`
- Las sugerencias son específicas al contexto y consideran:
  - Preferencias del vendedor
  - Estado actual del presupuesto
  - Metadata de los items (categoría, temporada, proveedor)

### Uso

```python
builder = BudgetBuilder(vendor_id="vendedor1")
builder.add_item(item)  # Las sugerencias se generan automáticamente
sugerencias = builder.get_suggestions()  # Obtener lista de sugerencias
