# Motor de Reglas de Negocio

## Descripción General

El Motor de Reglas de Negocio es un componente central que permite:
- Aplicar márgenes dinámicos
- Gestionar descuentos automáticos
- Manejar políticas de precios
- Validar restricciones comerciales

## Arquitectura

### 1. Modelos (`models.py`)

#### RuleType
Tipos de reglas soportados:
- `MARGIN`: Reglas de margen
- `DISCOUNT`: Reglas de descuento
- `PRICE`: Reglas de precio
- `AVAILABILITY`: Reglas de disponibilidad
- `RESTRICTION`: Reglas de restricción
- `VALIDATION`: Reglas de validación

#### Condition
Define una condición con:
- Campo a evaluar
- Operador
- Valor de comparación
- Metadatos

#### RuleAction
Define una acción a ejecutar:
- Tipo de acción
- Parámetros
- Metadatos

#### BusinessRule
Regla de negocio completa:
- Condiciones
- Acciones
- Prioridad
- Vigencia
- Metadatos

### 2. Motor de Reglas (`engine.py`)

El `BusinessRuleEngine` proporciona:
- Evaluación de reglas
- Cálculo de márgenes
- Aplicación de descuentos
- Validación de restricciones

## Objetivo Principal
Establecer un marco de reglas que garantice la consistencia y estabilidad durante las sesiones de venta, mientras permite la flexibilidad necesaria para adaptarse a las necesidades del negocio.

## Principios Fundamentales

### 1. Estabilidad Durante la Sesión
- Reglas inmutables durante la interacción con cliente
- Modificaciones controladas por el vendedor
- Validaciones no intrusivas

### 2. Control del Vendedor
- Control total sobre aplicación de reglas
- Decisiones informadas sobre excepciones
- Gestión completa del proceso de venta

### 3. Procesamiento Asíncrono
- Validaciones complejas post-sesión
- Actualizaciones de reglas diferidas
- Notificaciones controladas

## Tipos de Reglas

### 1. Reglas de Sesión (✅ IMPRESCINDIBLE)
```python
class SessionRules:
    def __init__(self):
        self.rules_snapshot = {}  # Reglas fijas durante la sesión
        self.modifications = []   # Cambios controlados

    def validate_modification(self, change: dict) -> bool:
        """Valida cambios durante la sesión."""
        pass
```

### 2. Reglas de Negocio (✅ IMPRESCINDIBLE)
```python
class BusinessRules:
    def apply_margins(self, package: dict) -> dict:
        """Aplica márgenes y reglas de precio."""
        pass

    def validate_business_rules(self, budget: Budget) -> bool:
        """Valida reglas de negocio básicas."""
        pass
```

### 3. Reglas de Validación (⚠️ PARCIALMENTE NECESARIO)
```python
class ValidationRules:
    def schedule_validation(self, budget: Budget):
        """Programa validación completa post-sesión."""
        pass

    def validate_async(self, budget: Budget):
        """Ejecuta validaciones asíncronas."""
        pass
```

## Priorización de Reglas

### 1. Reglas Críticas (✅ IMPRESCINDIBLE)
- Validación inmediata durante sesión
- Bloquean modificaciones inválidas
- Garantizan consistencia básica

### 2. Reglas Importantes (⚠️ PARCIALMENTE NECESARIO)
- Validación diferida post-sesión
- Generan advertencias
- Permiten override controlado

### 3. Reglas Opcionales (❌ OMITIBLE)
- Validación asíncrona
- Sugerencias y recomendaciones
- No bloquean operaciones

## Flujos de Trabajo

### 1. Aplicación de Reglas
```python
# 1. Inicializar reglas de sesión
session_rules = SessionRules()
session_rules.set_initial_rules(current_rules_snapshot)

# 2. Validar modificaciones
if session_rules.validate_modification(change):
    session.apply_modification(change)

# 3. Programar validaciones completas
validation_rules.schedule_validation(budget)
```

### 2. Actualización de Reglas
```python
# Las actualizaciones de reglas NO afectan sesiones activas
rules_manager.update_rules(new_rules)
rules_manager.apply_to_new_sessions()
```

## Características Principales

### 1. Evaluación de Reglas
```python
# Definir regla
rule = BusinessRule(
    id="high_season_margin",
    name="Margen Temporada Alta",
    type=RuleType.MARGIN,
    conditions=[
        Condition(
            field="temporal_data.season",
            operator=Operator.EQUALS,
            value="high"
        )
    ],
    actions=[
        RuleAction(
            action=Action.SET_MARGIN,
            parameters={"margin": 0.25}  # 25%
        )
    ],
    priority=1
)

# Evaluar reglas
results = engine.evaluate_rules(context)
```

### 2. Cálculo de Márgenes
```python
# Calcular margen
margin = engine.calculate_margin(context)

# Ejemplo de contexto
context = RuleContext(
    package_data={
        "base_price": 1000,
        "category": "premium"
    },
    temporal_data={
        "season": "high",
        "demand": "high"
    }
)
```

### 3. Gestión de Descuentos
```python
# Definir regla de descuento
discount_rule = BusinessRule(
    id="early_booking",
    name="Descuento Early Booking",
    type=RuleType.DISCOUNT,
    conditions=[
        Condition(
            field="temporal_data.days_to_travel",
            operator=Operator.GREATER_THAN,
            value=90
        )
    ],
    actions=[
        RuleAction(
            action=Action.APPLY_DISCOUNT,
            parameters={
                "discount": 10,  # 10%
                "is_percentage": True
            }
        )
    ]
)

# Aplicar descuentos
final_price = engine.apply_discounts(context, original_price)
```

## Integración con Otros Sistemas

### 1. Con el Sistema de Preferencias
- Reglas basadas en preferencias
- Personalización de márgenes
- Filtros automáticos

### 2. Con el Motor de Presupuestos
- Cálculo de precios finales
- Validación de restricciones
- Historial de cambios

### 3. Con la Interfaz de Vendedor
- Visualización de reglas aplicadas
- Simulación de escenarios
- Ajustes manuales

## Monitoreo y Métricas

- `rule_evaluations_total`: Evaluaciones de reglas
- `rule_processing_seconds`: Tiempo de procesamiento

## Métricas de Rendimiento

### 1. Tiempos de Respuesta
- Validación básica < 100ms
- Validación completa < 1 segundo
- Actualización de reglas < 2 segundos

### 2. Precisión
- 100% cumplimiento de reglas críticas
- Validación completa post-sesión
- Trazabilidad de excepciones

### 3. Estabilidad
- Zero conflictos durante sesión
- Consistencia garantizada
- Recuperación automática

## Integración con Otros Módulos

### 1. Motor de Presupuestos
- Validaciones síncronas básicas
- Validaciones asíncronas completas
- Estado consistente

### 2. Interfaz de Vendedor
- Feedback inmediato de validaciones
- Indicadores claros de estado
- Control sobre excepciones

## Próximas Mejoras

### 1. Optimizaciones (❌ OMITIBLE)
- Motor de reglas avanzado
- Aprendizaje automático
- Predicción de impacto

### 2. Reglas Avanzadas
   - Reglas compuestas
   - Condiciones temporales
   - Prioridades dinámicas

### 3. Machine Learning
   - Optimización automática de márgenes
   - Predicción de demanda
   - Recomendación de reglas

### 4. Personalización
   - Reglas por mercado
   - Reglas por segmento
   - Reglas por canal

### 5. Auditoría y Análisis
   - Registro detallado
   - Análisis de impacto
   - Optimización basada en datos
