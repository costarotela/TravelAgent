# Sistema de Preferencias

## Descripción General

El Sistema de Preferencias es un componente central que permite personalizar la experiencia tanto para clientes como para vendedores. Sus principales funciones son:
- Almacenar y gestionar preferencias de usuarios
- Aplicar reglas definidas por vendedores
- Personalizar presupuestos según preferencias
- Aplicar filtros automáticos a resultados

## Arquitectura

### 1. Modelos (`models.py`)

#### PreferenceType
Tipos de preferencias soportados:
- `BUDGET`: Preferencias de presupuesto
- `TRAVEL`: Preferencias de viaje
- `NOTIFICATION`: Preferencias de notificación
- `DISPLAY`: Preferencias de visualización
- `VENDOR`: Preferencias del vendedor
- `FILTER`: Filtros personalizados

#### UserPreferences
- Almacena preferencias por usuario
- Mantiene historial de actualizaciones
- Incluye metadatos y trazabilidad

#### VendorRule
- Define reglas configurables por vendedores
- Sistema de prioridades
- Condiciones y acciones personalizables

#### FilterConfig
- Configuración de filtros automáticos
- Criterios flexibles de filtrado
- Metadatos para tracking

### 2. Gestor de Preferencias (`manager.py`)

El `PreferenceManager` proporciona:
- Gestión de preferencias de usuario
- Aplicación de reglas de vendedor
- Filtrado automático de resultados
- Integración con métricas

## Características Principales

### 1. Gestión de Preferencias
```python
# Ejemplo de uso
manager = PreferenceManager(storage_backend)

# Establecer preferencia
await manager.set_preference(
    user_id="user123",
    pref_type=PreferenceType.TRAVEL,
    key="preferred_destinations",
    value=["Cancún", "Punta Cana"],
)

# Obtener preferencias
prefs = await manager.get_user_preferences("user123")
```

### 2. Reglas de Vendedor
```python
# Definir regla
rule = VendorRule(
    name="high_value_client",
    description="Descuento para clientes premium",
    preference_type=PreferenceType.BUDGET,
    conditions={"client_type": "premium"},
    actions={
        "set_preference": {
            "key": "discount_percentage",
            "value": 10
        }
    },
    priority=1,
)

# Agregar regla
manager.add_vendor_rule(rule)

# Aplicar reglas
await manager.apply_vendor_rules(
    user_id="user123",
    context={"client_type": "premium"},
)
```

### 3. Filtros Automáticos
```python
# Configurar filtro
filter_config = FilterConfig(
    name="price_range",
    description="Filtrar por rango de precio",
    filter_type="price",
    criteria={
        "min": 1000,
        "max": 5000
    },
)

# Agregar filtro
manager.add_filter_config(filter_config)

# Aplicar filtros
filtered_data = manager.apply_filters(
    data=packages,
    user_id="user123",
)
```

## Integración con Otros Sistemas

### 1. Con el Sistema de Recolección
- Filtrado automático de resultados
- Priorización según preferencias
- Personalización de búsquedas

### 2. Con el Motor de Presupuestos
- Ajuste de márgenes según perfil
- Aplicación de descuentos automáticos
- Personalización de versiones

### 3. Con el Sistema de Notificaciones
- Preferencias de comunicación
- Umbrales personalizados
- Canales preferidos

## Monitoreo y Métricas

- `preference_updates_total`: Actualizaciones de preferencias
- `preference_processing_time`: Tiempo de procesamiento

## Próximas Mejoras

1. **Aprendizaje Automático**
   - Inferencia de preferencias
   - Recomendaciones personalizadas
   - Optimización automática

2. **Segmentación Avanzada**
   - Perfiles de usuario dinámicos
   - Reglas basadas en segmentos
   - Personalización por mercado

3. **Integración y Extensibilidad**
   - API para gestión de preferencias
   - Plugins personalizados
   - Sincronización multi-dispositivo
