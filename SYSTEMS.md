# Sistemas del Smart Travel Agent

Este documento describe en detalle los diferentes sistemas que componen el Smart Travel Agent.

## Sistema de Sugerencias

### 🎯 Propósito
Sistema diseñado para optimizar presupuestos de viaje de forma automática, proporcionando sugerencias inteligentes al vendedor durante la construcción del presupuesto.

### 🔍 Tipos de Sugerencias

#### 1. 💰 Optimización de Costos
- **Activación**: Items con costo > $1000 USD
- **Objetivo**: Encontrar alternativas más económicas
- **Ahorro Potencial**: Hasta 20%
- **Acción**: Botón "Ver Alternativa"
- **Uso**: Ideal para ajustarse al presupuesto del cliente sin sacrificar calidad

#### 2. 📅 Temporada
- **Activación**: Items marcados como temporada alta
- **Objetivo**: Sugerir fechas alternativas más económicas
- **Ahorro Potencial**: Hasta 30%
- **Acción**: Botón "Cambiar Fecha"
- **Uso**: Optimizar costos mediante selección inteligente de fechas

#### 3. 📦 Paquetes
- **Activación**: Múltiples items del mismo proveedor
- **Objetivo**: Combinar items en paquetes con descuento
- **Ahorro Potencial**: Hasta 15%
- **Acción**: Botón "Ver Paquete"
- **Uso**: Aprovechar descuentos por volumen o paquetes predefinidos

### 💻 Implementación Técnica

```python
# Generación de Sugerencias
def _generate_suggestions(self) -> List[str]:
    suggestions = []
    
    # Análisis de costos
    for item in self.items:
        if item.amount > Decimal('1000'):
            suggestions.append(f"💰 Hay una alternativa más económica para '{item.description}' que podría ahorrar hasta un 20%")
    
    # Análisis de temporada
    for item in self.items:
        if item.metadata.get('season') == 'high':
            suggestions.append(f"📅 El item '{item.description}' es más económico en temporada media. Cambiar la fecha podría ahorrar hasta 30%")
    
    # Análisis de paquetes
    provider_items = {}
    for item in self.items:
        provider = item.metadata.get('provider_id')
        if provider:
            provider_items.setdefault(provider, []).append(item)
    
    for provider, items in provider_items.items():
        if len(items) >= 2:
            descriptions = [item.description for item in items]
            suggestions.append(f"📦 Hay un paquete disponible que incluye: {', '.join(descriptions)}. Ahorro potencial del 15%")
```

### 📱 Interfaz de Usuario
- **Dashboard**: Visualización categorizada de sugerencias
- **Expansores**: Agrupación por tipo de sugerencia
- **Botones de Acción**: Acciones específicas para cada tipo
- **Feedback Visual**: Íconos y colores para mejor UX

### 📋 Guía para el Vendedor

#### Flujo de Trabajo
1. Agregar items al presupuesto normalmente
2. El sistema genera sugerencias automáticamente
3. Revisar sección "🎯 Sugerencias de Optimización"
4. Expandir categorías relevantes
5. Usar botones de acción según necesidad

#### Ejemplo de Uso
```
1. Vendedor agrega "Hotel de Lujo en Cancún" ($1500)
2. Sistema sugiere alternativa económica (-20%)
3. Vendedor agrega dos tours del mismo proveedor
4. Sistema sugiere paquete combinado (-15%)
5. Vendedor explora alternativas usando botones de acción
```

### 🎁 Beneficios
- Ahorro de tiempo en búsqueda de alternativas
- Optimización automática de costos
- Mejor servicio al cliente
- Aprovechamiento de descuentos
- Decisiones informadas basadas en datos

### 🔄 Mantenimiento
- Actualizar umbrales de precio según inflación
- Ajustar porcentajes de ahorro según datos reales
- Mantener lista de proveedores actualizada
- Revisar efectividad de sugerencias periódicamente
