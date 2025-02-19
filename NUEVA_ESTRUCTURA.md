# Nueva Estructura SmartTravelAgent

## Estructura de Directorios

```
SmartTravelAgent/
├── travel_agent/                # Paquete principal
│   ├── core/                   # Núcleo del sistema
│   │   ├── collectors/        # ✅ IMPRESCINDIBLE
│   │   │   ├── browser/       # Automatización de navegación
│   │   │   ├── scraper/       # Motor de scraping
│   │   │   └── api/           # Integraciones con APIs
│   │   │
│   │   ├── analysis/         # ✅ IMPRESCINDIBLE
│   │   │   ├── optimizer.py   # Optimización multi-pasada
│   │   │   ├── comparator.py  # Comparación de ofertas
│   │   │   └── recommender.py # Sistema de recomendaciones
│   │   │
│   │   ├── session/          # ✅ IMPRESCINDIBLE
│   │   │   ├── manager.py     # Gestión de sesiones
│   │   │   ├── stability.py   # Protección de estabilidad
│   │   │   └── changes.py     # Tracking de cambios
│   │   │
│   │   └── budget/           # ✅ IMPRESCINDIBLE
│   │       ├── engine.py      # Motor de presupuestos
│   │       ├── optimizer.py   # Optimización iterativa
│   │       └── builder.py     # Constructor dinámico
│   │
│   ├── providers/             # ⚠️ PARCIALMENTE NECESARIO
│   │   ├── base.py           # Base para proveedores
│   │   ├── scrapers/         # Scrapers específicos
│   │   │   ├── hotels/
│   │   │   ├── flights/
│   │   │   └── packages/
│   │   └── normalizers/      # Normalización de datos
│   │
│   ├── interface/            # ✅ IMPRESCINDIBLE
│   │   ├── dashboard/        # Dashboard principal
│   │   │   ├── templates/    # Templates HTML
│   │   │   └── static/       # Assets
│   │   │
│   │   ├── budget_editor/    # Editor de presupuestos
│   │   │   ├── components/   # Componentes UI
│   │   │   └── controls/     # Controles de edición
│   │   │
│   │   └── api/             # API REST
│   │       ├── routes/      # Rutas API
│   │       └── schemas/     # Schemas API
│   │
│   └── schemas/            # ✅ IMPRESCINDIBLE
│       ├── budget.py      # Schemas de presupuestos
│       ├── provider.py    # Schemas de proveedores
│       └── session.py     # Schemas de sesión
│
├── data/                  # Datos persistentes
│   ├── cache/            # Caché de datos
│   └── db/               # Base de datos
│
├── tests/                # Tests
│   ├── unit/            # Tests unitarios
│   └── integration/     # Tests de integración
│
└── docs/                # Documentación actualizada
    └── nueva_arquitectura.md
```

## Alineación con Objetivos

1. **Motor de Recolección y Análisis**
   - `core/collectors/`: Extracción de datos
   - `core/analysis/`: Análisis y optimización
   - `providers/scrapers/`: Implementaciones específicas

2. **Optimización Multi-pasada**
   - `core/analysis/optimizer.py`: Motor de optimización
   - `core/budget/optimizer.py`: Optimización de presupuestos
   - `core/analysis/comparator.py`: Comparación de ofertas

3. **Control del Vendedor**
   - `interface/dashboard/`: Dashboard principal
   - `interface/budget_editor/`: Herramientas de edición
   - `core/session/stability.py`: Protección de estabilidad

4. **Estabilidad de Sesión**
   - `core/session/manager.py`: Gestión de sesiones
   - `core/session/stability.py`: Garantía de estabilidad
   - `core/session/changes.py`: Control de cambios

## Prioridades de Implementación

### IMPRESCINDIBLE (✅)
1. Motor de recolección y análisis
2. Sistema de optimización multi-pasada
3. Control de estabilidad de sesión
4. Interfaz básica del vendedor

### PARCIALMENTE NECESARIO (⚠️)
1. Implementaciones específicas de scrapers
2. Sistema de caché básico
3. Herramientas avanzadas de edición

### OMITIBLE (❌)
1. Optimizaciones de rendimiento
2. Análisis predictivo
3. Características UI avanzadas
