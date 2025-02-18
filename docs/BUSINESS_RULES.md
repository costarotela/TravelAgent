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

## Próximas Mejoras

1. **Reglas Avanzadas**
   - Reglas compuestas
   - Condiciones temporales
   - Prioridades dinámicas

2. **Machine Learning**
   - Optimización automática de márgenes
   - Predicción de demanda
   - Recomendación de reglas

3. **Personalización**
   - Reglas por mercado
   - Reglas por segmento
   - Reglas por canal

4. **Auditoría y Análisis**
   - Registro detallado
   - Análisis de impacto
   - Optimización basada en datos
