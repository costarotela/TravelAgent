# Sistema de Análisis 🧠

## Descripción General
El Sistema de Análisis es un componente avanzado que procesa los datos recopilados por el Sistema de Observación para generar insights profundos y recomendaciones accionables.

## Componentes Principales

### 1. MarketInsight
Modelo que representa un insight completo del mercado:
- Ruta (origen y destino)
- Tendencias de precios y demanda
- Volatilidad del mercado
- Patrones estacionales
- Recomendaciones
- Nivel de confianza
- Datos de soporte

### 2. AnalysisSystem
Sistema principal que realiza análisis detallados:

#### 2.1 Análisis de Precios
- **Tendencias**:
  - `strongly_bullish`: >10% incremento
  - `bullish`: 5-10% incremento
  - `neutral`: ±5% cambio
  - `bearish`: 5-10% decremento
  - `strongly_bearish`: >10% decremento

- **Volatilidad**:
  - Calculada usando coeficiente de variación
  - Expresada como porcentaje
  - Indica estabilidad del mercado

#### 2.2 Análisis de Demanda
- **Tendencias**:
  - `very_high`: >20% incremento
  - `high`: 10-20% incremento
  - `stable`: ±10% cambio
  - `low`: 10-20% decremento
  - `very_low`: >20% decremento

#### 2.3 Análisis de Estacionalidad
- **Patrones**:
  - `highly_seasonal`: >15% variación
  - `moderately_seasonal`: 8-15% variación
  - `non_seasonal`: <8% variación

### 3. Sistema de Recomendaciones
Genera recomendaciones basadas en múltiples factores:

#### 3.1 Tipos de Recomendaciones
- `strong_buy`: Alta demanda, precios bajando
- `strong_sell`: Baja demanda, precios subiendo
- `high_risk`: Alta volatilidad
- `hold`: Mercado estable
- `seasonal_opportunity`: Oportunidad estacional
- `monitor`: Situación requiere seguimiento

#### 3.2 Factores de Confianza
- Tamaño de la muestra
- Volatilidad del mercado
- Calidad de datos
- Consistencia de patrones

## Integración con Otros Sistemas

### 1. Base de Datos
- Acceso a histórico de paquetes
- Análisis de mercado previos
- Almacenamiento de insights

### 2. Sistema de Caché
- Almacenamiento temporal de insights
- TTL de 1 hora
- Mejora rendimiento

## Uso del Sistema

### 1. Análisis de Ruta
```python
insight = await analysis_system.analyze_route(
    origin="Buenos Aires",
    destination="Madrid"
)
```

### 2. Interpretación de Resultados
```python
if insight:
    print(f"Tendencia: {insight.price_trend}")
    print(f"Volatilidad: {insight.price_volatility}%")
    print(f"Recomendación: {insight.recommendation}")
```

## Próximas Mejoras

1. **Análisis Avanzado**
   - Machine Learning para predicciones
   - Análisis de sentimiento
   - Correlaciones entre rutas

2. **Factores Adicionales**
   - Eventos especiales
   - Indicadores económicos
   - Factores geopolíticos

3. **Optimización**
   - Análisis en tiempo real
   - Procesamiento paralelo
   - Aprendizaje continuo
