# Módulo de Presupuestos

Este es el módulo central del sistema SmartTravelAgent, responsable de la creación y gestión de presupuestos.

## Componentes

### 1. PriceTracker (`price_tracker.py`)
Seguimiento simple de precios para presupuestos.

```python
# Seguimiento de precio
await price_tracker.track_price(package)

# Obtener historial
history = await price_tracker.get_price_history(package_id)
```

### 2. BudgetRules (`rules.py`)
Reglas básicas para la creación de presupuestos.

```python
# Aplicar margen
final_price = rules.apply_margin(base_price, "corporate")

# Validar items
errors = rules.validate_budget_items(budget_items)

# Verificar disponibilidad
is_available = rules.check_availability(package)
```

## Uso Correcto

1. **Seguimiento de Precios**
   - Usar `PriceTracker` para registrar precios
   - Consultar historial reciente para referencia
   - NO usar para análisis de mercado complejo

2. **Reglas de Negocio**
   - Usar `BudgetRules` para márgenes y validación
   - Mantener reglas simples y directas
   - NO agregar lógica compleja de negocio

3. **Validación**
   - Validar items antes de crear presupuesto
   - Verificar disponibilidad en tiempo real
   - Mantener feedback inmediato al vendedor

## Advertencias

1. NO agregar:
   - Análisis complejo de precios
   - Predicciones de mercado
   - Reglas de negocio complejas

2. Mantener el foco en:
   - Creación de presupuestos
   - Asistencia al vendedor
   - Datos actualizados

## Ejemplos de Uso

### Creación de Presupuesto
```python
# 1. Verificar disponibilidad
if rules.check_availability(package):
    # 2. Registrar precio
    await price_tracker.track_price(package)

    # 3. Aplicar margen
    final_price = rules.apply_margin(package.price, client_type)

    # 4. Validar
    errors = rules.validate_budget_items({
        "flight": {"price": final_price, "date": "2024-03-01"}
    })
```

### Actualización de Presupuesto
```python
# 1. Obtener historial
history = await price_tracker.get_price_history(package_id)

# 2. Verificar cambios
if history["current_price"] != original_price:
    # 3. Recalcular con nuevos precios
    new_price = rules.apply_margin(history["current_price"], client_type)
```
