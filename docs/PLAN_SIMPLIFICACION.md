# Plan de Simplificación y Priorización

## 1. Componentes a Simplificar

### Sistema de Monitoreo
- **Actual**: FastAPI + Prometheus + Streamlit dashboard complejo
- **Simplificación**: 
  - Mantener solo logs básicos en archivo
  - Métricas simples en SQLite
  - Dashboard Streamlit básico con métricas esenciales

### Sistema de Caché
- **Actual**: Redis con TTL configurable
- **Simplificación**:
  - Migrar a TTLCache en memoria
  - Implementar solo para búsquedas frecuentes
  - Postergar Redis para fase de escalamiento

### Autenticación
- **Actual**: Sistema complejo de auth
- **Simplificación**:
  - Implementar solo login básico
  - Usar sesiones simples de Streamlit
  - Postergar roles y permisos avanzados

## 2. Prioridades Inmediatas

### 2.1 Proveedor Aero (2-3 semanas)
1. **Semana 1**: Implementación básica
   - Scraping de búsqueda de vuelos
   - Extracción de datos de hoteles
   - Almacenamiento simple en SQLite

2. **Semana 2**: Integración
   - Generación de presupuestos básicos
   - Interfaz de búsqueda simple
   - Visualización de resultados en tablas

3. **Semana 3**: Refinamiento
   - Manejo de errores básico
   - Caché simple en memoria
   - Pruebas básicas de integración

### 2.2 Funcionalidades Core (3-4 semanas)

1. **Búsqueda Básica**
   - Formulario simple de búsqueda
   - Filtros básicos (fecha, destino, precio)
   - Visualización tabular de resultados

2. **Presupuestos**
   - Generación de presupuesto simple
   - Exportación a PDF básica
   - Guardado en SQLite

3. **Interfaz de Usuario**
   - Streamlit con 3-4 páginas principales
   - Formularios básicos
   - Tablas y gráficos simples

## 3. Estructura Simplificada del Proyecto

```
src/
├── core/
│   ├── providers/
│   │   ├── aero.py      # Proveedor Aero
│   │   └── base.py      # Clase base
│   ├── search.py        # Búsqueda simple
│   └── budget.py        # Generación presupuestos
├── ui/
│   ├── pages/           # Páginas Streamlit
│   └── components/      # Componentes UI básicos
└── utils/
    ├── cache.py         # TTLCache simple
    └── storage.py       # SQLite helpers
```

## 4. Métricas de Éxito MVP

1. **Funcionalidad**
   - Búsqueda exitosa en Aero: > 90%
   - Tiempo de respuesta: < 5s
   - Generación de presupuesto: < 10s

2. **Usabilidad**
   - Completar búsqueda: < 3 pasos
   - Generar presupuesto: < 2 clicks
   - Exportar resultado: 1 click

## 5. Próximos Pasos

1. Comenzar simplificación del sistema de monitoreo
2. Migrar caché a solución en memoria
3. Iniciar implementación de Aero
4. Desarrollar interfaz básica de búsqueda

## 6. Qué NO Hacer Ahora

1. ❌ No agregar más proveedores
2. ❌ No implementar análisis predictivo
3. ❌ No desarrollar APIs públicas
4. ❌ No agregar más métricas de monitoreo
5. ❌ No implementar características avanzadas de UI

## Nota Importante
Este es un ejemplo de plan de simplificación y priorización que utiliza datos simulados para demostrar el flujo de trabajo. Los vuelos mostrados son generados automáticamente y no representan vuelos reales. Los precios son aleatorios y solo sirven como ejemplo. El proveedor `AeroProvider` es un mock que simula la búsqueda de vuelos. La base de datos es temporal y se reinicia en cada ejecución.
