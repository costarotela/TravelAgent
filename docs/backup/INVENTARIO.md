# Inventario del Proyecto

## 1. Paquetes Principales

### smart_travel_agency/
- Core del sistema
- Interfaces de usuario
- Modelos de datos
- Proveedores

### agent_core/
- Scraping
- Gestión de sesiones
- Reconstrucción (nuevo)
- Schemas duplicados

### src/
- Interfaces web
- Templates
- Assets
- Controladores

## 2. Bases de Datos

- `/data/travel_agency.db`
- `/data/storage.db`
- `/cache/cache.db`
- `/metrics.db`

## 3. Problemas Identificados

### 3.1 Duplicación de Código
- Schemas duplicados entre paquetes
- Múltiples implementaciones de sesiones
- Interfaces redundantes

### 3.2 Desorganización
- Código disperso en múltiples directorios
- Sin estructura clara
- Sin separación de responsabilidades

### 3.3 Bases de Datos
- Múltiples bases sin propósito claro
- Ubicaciones inconsistentes
- Posible pérdida de datos

## 4. Plan de Reorganización

### 4.1 Nueva Estructura
```
SmartTravelAgency/
├── smart_travel_agency/           # ÚNICO paquete principal
│   ├── core/                     # Lógica core
│   │   ├── session/             # Gestión de sesiones
│   │   ├── budget/              # Motor de presupuestos
│   │   └── reconstruction/      # Sistema de reconstrucción
│   ├── providers/               # Integración con proveedores
│   │   ├── base.py             # Base para proveedores
│   │   ├── ola/                # Implementación OLA
│   │   └── scrapers/           # Sistema de scraping
│   ├── interface/              # Interfaces de usuario
│   │   ├── web/               # Interfaz web
│   │   └── api/               # API REST
│   └── schemas/               # ÚNICO lugar para schemas
├── data/                      # ÚNICO lugar para datos
│   └── db/                   # Bases de datos
├── tests/                    # Tests
├── docs/                     # Documentación
└── scripts/                  # Scripts de utilidad
```

### 4.2 Pasos de Migración

1. **Fase 1: Consolidación**
   - Mover todo código de `agent_core/` a `smart_travel_agency/`
   - Eliminar duplicados
   - Unificar schemas

2. **Fase 2: Reorganización**
   - Estructurar directorios según nueva estructura
   - Mover archivos a ubicaciones correctas
   - Actualizar imports

3. **Fase 3: Limpieza**
   - Eliminar código obsoleto
   - Unificar bases de datos
   - Actualizar documentación

4. **Fase 4: Validación**
   - Verificar funcionalidad
   - Ejecutar tests
   - Validar integridad

## 5. Prioridades

### 5.1 IMPRESCINDIBLE (✅)
1. Consolidar código en un solo paquete
2. Unificar schemas
3. Reorganizar estructura de directorios

### 5.2 PARCIALMENTE NECESARIO (⚠️)
1. Unificar bases de datos
2. Actualizar documentación
3. Mejorar organización de tests

### 5.3 OMITIBLE (❌)
1. Optimizaciones de código
2. Refactoring no crítico
3. Mejoras cosméticas
