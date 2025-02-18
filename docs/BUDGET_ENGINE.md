# Sistema de Actualización de Presupuestos

## Descripción General

El Sistema de Actualización de Presupuestos es un componente central del Smart Travel Agency que se encarga de:
- Detectar cambios en precios y disponibilidad de paquetes turísticos
- Recalcular presupuestos automáticamente
- Aplicar reglas de negocio configurables
- Mantener historial de cambios
- Notificar cambios significativos

## Arquitectura

El sistema está compuesto por los siguientes módulos principales:

### 1. Modelos (`models.py`)

#### Budget
- Modelo principal que representa un presupuesto completo
- Mantiene historial de versiones
- Incluye información del cliente y metadatos
- Propiedades para acceso rápido a versión actual y estadísticas

#### BudgetVersion
- Representa una versión específica del presupuesto
- Contiene lista de paquetes y precios calculados
- Registra cambios específicos de la versión
- Incluye porcentaje de markup y precios finales

#### BudgetChange
- Registra cambios individuales en paquetes
- Tipos de cambios soportados:
  - `PRICE_INCREASE`: Aumento de precios
  - `PRICE_DECREASE`: Disminución de precios
  - `AVAILABILITY_CHANGE`: Cambios en disponibilidad
  - `DATES_CHANGE`: Cambios en fechas
  - `PACKAGE_REMOVED`: Paquete eliminado
  - `PACKAGE_ADDED`: Nuevo paquete
  - `DETAILS_CHANGE`: Cambios en detalles

#### BudgetRule
- Define reglas de negocio configurables
- Incluye condiciones y acciones
- Sistema de prioridades
- Metadatos para tracking

### 2. Motor de Reglas (`rules.py`)

El `RuleEngine` se encarga de:
- Evaluar cambios entre versiones de paquetes
- Aplicar reglas de negocio en orden de prioridad
- Calcular ajustes de precios
- Mantener registro de reglas aplicadas

Ejemplo de reglas:
```python
rules = [
    BudgetRule(
        name="price_protection",
        description="Proteger clientes de aumentos significativos",
        condition={"type": "price_increase", "threshold": 10},
        action={"type": "apply_discount", "value": 5},
        priority=1,
    ),
    BudgetRule(
        name="low_availability",
        description="Aumentar markup en paquetes con baja disponibilidad",
        condition={"type": "availability_low", "threshold": 5},
        action={"type": "increase_markup", "value": 2},
        priority=2,
    ),
]
```

### 3. Motor Principal (`engine.py`)

El `BudgetUpdateEngine` proporciona:
- Creación de presupuestos
- Actualización automática basada en nuevos datos
- Integración con sistema de notificaciones
- Métricas y monitoreo
- Manejo de errores robusto

## Características Avanzadas

### 1. Monitoreo y Métricas
- Integración con Prometheus
- Métricas clave:
  - `budget_updates_total`: Total de actualizaciones
  - `budget_processing_seconds`: Tiempo de procesamiento
  - `rule_applications_total`: Aplicación de reglas

### 2. Sistema de Notificaciones
- Notificaciones automáticas de cambios significativos
- Soporte para múltiples canales (email, Slack)
- Personalización de umbrales de notificación

### 3. Validación y Seguridad
- Validación de datos con Pydantic
- Registro detallado de cambios
- Trazabilidad completa de modificaciones

### 4. Integración con Recolector de Datos
- Actualización automática desde múltiples proveedores
- Caché inteligente para optimizar rendimiento
- Manejo de errores y reintentos

## Ejemplo de Uso

```python
from src.core.budget_engine import BudgetUpdateEngine, BudgetRule
from src.core.collectors import DataCollector
from src.core.notifications import NotificationManager

async def main():
    # Configurar motor
    rules = [
        BudgetRule(
            name="price_protection",
            description="Proteger clientes de aumentos significativos",
            condition={"type": "price_increase", "threshold": 10},
            action={"type": "apply_discount", "value": 5},
            priority=1,
        )
    ]
    
    notification_manager = NotificationManager()
    engine = BudgetUpdateEngine(rules, notification_manager)
    
    # Crear presupuesto inicial
    budget = engine.create_budget(
        client_name="John Doe",
        client_email="john@example.com",
        packages=initial_packages,
        markup_percentage=0.15,
    )
    
    # Actualizar con nuevos datos
    collector = DataCollector(providers)
    new_packages = await collector.collect_data("Cancún")
    updated_budget = engine.update_budget(budget, new_packages)
    
    # Ver cambios
    for version in updated_budget.versions:
        print(f"Version {version.version}:")
        for change in version.changes:
            print(f"- {change.change_type}: {change.metadata}")
```

## Próximas Mejoras

1. **Optimización de Rendimiento**
   - Implementar caché distribuido
   - Optimizar procesamiento de reglas
   - Mejorar manejo de memoria

2. **Funcionalidades Adicionales**
   - Más tipos de reglas de negocio
   - Análisis predictivo de cambios
   - Recomendaciones automáticas

3. **Integración y Extensibilidad**
   - API REST para gestión de reglas
   - Más proveedores de datos
   - Plugins personalizados
