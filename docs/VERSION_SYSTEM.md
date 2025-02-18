# Sistema de Versionado de Presupuestos

## Descripción General

El Sistema de Versionado de Presupuestos permite:
- Mantener múltiples versiones activas
- Comparar diferentes escenarios
- Gestionar cambios incrementales
- Permitir rollback de cambios

## Arquitectura

### 1. Modelos (`models.py`)

#### ChangeType
Tipos de cambios soportados:
- `PRICE`: Cambios en precios
- `PACKAGE`: Cambios en paquetes
- `MARGIN`: Cambios en márgenes
- `DISCOUNT`: Cambios en descuentos
- `RULE`: Cambios en reglas
- `PREFERENCE`: Cambios en preferencias
- `METADATA`: Cambios en metadatos

#### Version
Versión de un presupuesto:
- Número de versión
- Cambios incluidos
- Metadatos y trazabilidad
- Estado (activo, archivado)

#### Branch
Rama de versiones:
- Versión base
- Lista de versiones
- Estado (activo, archivado, fusionado)

### 2. Gestor de Versiones (`manager.py`)

El `VersionManager` proporciona:
- Creación de versiones
- Gestión de ramas
- Fusión de versiones
- Comparación de versiones

## Características Principales

### 1. Gestión de Versiones
```python
# Crear nueva versión
version = await manager.create_version(
    budget_id="budget123",
    name="Ajuste de Precios",
    changes=[
        Change(
            type=ChangeType.PRICE,
            field="package.price",
            old_value=1000,
            new_value=1200,
            author="vendor1"
        )
    ]
)

# Obtener versión
version = await manager.get_version("budget123_v1")
```

### 2. Gestión de Ramas
```python
# Crear rama
branch = await manager.create_branch(
    budget_id="budget123",
    name="Temporada Alta",
    base_version_id="budget123_v1",
    description="Ajustes para temporada alta"
)

# Fusionar ramas
result = await manager.merge_versions(
    source_version_id="budget123_v2",
    target_version_id="budget123_v1",
    strategy=MergeStrategy.MANUAL
)
```

### 3. Comparación de Versiones
```python
# Comparar versiones
diff = await manager.compare_versions(
    base_version_id="budget123_v1",
    target_version_id="budget123_v2"
)

# Visualizar grafo de versiones
graph = await manager.get_version_graph("budget123")
```

## Integración con Otros Sistemas

### 1. Con el Motor de Presupuestos
- Versionado de cambios
- Historial de modificaciones
- Rollback de cambios

### 2. Con el Motor de Reglas
- Versionado de reglas
- Cambios en políticas
- Validación de restricciones

### 3. Con la Interfaz de Vendedor
- Visualización de versiones
- Comparación de escenarios
- Gestión de cambios

## Monitoreo y Métricas

- `version_operations_total`: Operaciones de versionado
- `version_processing_time`: Tiempo de procesamiento

## Próximas Mejoras

1. **Versionado Avanzado**
   - Etiquetas y tags
   - Snapshots automáticos
   - Políticas de retención

2. **Colaboración**
   - Bloqueo de versiones
   - Revisión de cambios
   - Comentarios y notas

3. **Análisis**
   - Estadísticas de cambios
   - Patrones de modificación
   - Impacto de cambios

4. **Automatización**
   - Merge automático
   - Resolución de conflictos
   - Validación de cambios
