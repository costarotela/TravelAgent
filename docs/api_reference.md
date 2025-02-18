# API Reference - Smart Travel Agency

## Core APIs

### Análisis de Precios

#### `analyze_price(context: AnalysisContext) -> PriceAnalysis`
Analiza tendencias y variaciones de precios.

**Parámetros:**
- `context`: Contexto del análisis
  - `package_data`: Datos del paquete
  - `historical_prices`: Historial de precios
  - `market_data`: Datos del mercado

**Retorna:**
- `PriceAnalysis`: Análisis de precios
  - `trend`: Tendencia (INCREASING, DECREASING, STABLE, VOLATILE)
  - `confidence`: Nivel de confianza
  - `expected_variation`: Variación esperada
  - `factors`: Factores influyentes

**Ejemplo:**
```python
analysis = await engine.analyze_price(context)
print(f"Tendencia: {analysis.trend}")
print(f"Variación esperada: {analysis.expected_variation}%")
```

### Análisis de Proveedores

#### `analyze_supplier(context: AnalysisContext, supplier_id: str) -> SupplierAnalysis`
Analiza rendimiento y métricas de proveedor.

**Parámetros:**
- `context`: Contexto del análisis
- `supplier_id`: ID del proveedor

**Retorna:**
- `SupplierAnalysis`: Análisis del proveedor
  - `metrics`: Métricas de rendimiento
  - `historical_performance`: Rendimiento histórico
  - `recommendations`: Recomendaciones

**Ejemplo:**
```python
analysis = await engine.analyze_supplier(context, "PROV001")
print(f"Confiabilidad: {analysis.metrics.reliability_score}")
print(f"Recomendaciones: {analysis.recommendations}")
```

## Modelos de Datos

### `PriceTrend`
```python
class PriceTrend(str, Enum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"
```

### `ConfidenceLevel`
```python
class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
```

### `PriceAnalysis`
```python
class PriceAnalysis(BaseModel):
    item_id: str
    current_price: float
    historical_prices: List[Dict[str, Any]]
    trend: PriceTrend
    confidence: ConfidenceLevel
    expected_variation: float
    factors: List[str]
```

### `SupplierMetrics`
```python
class SupplierMetrics(BaseModel):
    reliability_score: float
    price_competitiveness: float
    service_quality: float
    response_time: float
```

### `SupplierAnalysis`
```python
class SupplierAnalysis(BaseModel):
    supplier_id: str
    service_type: str
    metrics: SupplierMetrics
    historical_performance: List[Dict[str, Any]]
    confidence: ConfidenceLevel
    recommendations: List[str]
```

## Métricas y Monitoreo

### Contadores
```python
METRICS["analysis_operations"] = Counter(
    "analysis_operations_total",
    "Total number of analysis operations",
    ["analysis_type"],
)
```

### Histogramas
```python
METRICS["analysis_processing_time"] = Histogram(
    "analysis_processing_seconds",
    "Time taken to process analysis",
)
```

## Errores y Excepciones

### `AnalysisError`
Error base para operaciones de análisis.

```python
class AnalysisError(Exception):
    """Error base para operaciones de análisis."""
    pass
```

### `InvalidContextError`
Error por contexto de análisis inválido.

```python
class InvalidContextError(AnalysisError):
    """Error por contexto de análisis inválido."""
    pass
```

### `SupplierNotFoundError`
Error cuando no se encuentra un proveedor.

```python
class SupplierNotFoundError(AnalysisError):
    """Error cuando no se encuentra un proveedor."""
    pass
```

## Utilidades

### Preparación de Datos
```python
def prepare_price_data(historical_prices: List[Dict[str, Any]]) -> pd.DataFrame:
    """Prepara datos históricos de precios para análisis."""
    df = pd.DataFrame(historical_prices)
    df = df.rename(columns={
        "timestamp": "ds",
        "price": "y"
    })
    return df.sort_values("ds")
```

### Cálculo de Confianza
```python
def calculate_confidence(
    forecast: pd.DataFrame,
    historical_data: List[Dict[str, Any]],
) -> ConfidenceLevel:
    """Calcula nivel de confianza del análisis."""
    mape = calculate_mape(forecast)
    r2 = calculate_r2(forecast)
    
    if mape < 10 and r2 > 0.8:
        return ConfidenceLevel.HIGH
    elif mape < 20 and r2 > 0.6:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW
```

## Ejemplos de Uso

### Análisis Completo
```python
async def analyze_package(package_id: str):
    # Preparar contexto
    context = AnalysisContext(
        package_data=get_package_data(package_id),
        historical_prices=get_historical_prices(package_id),
        market_data=get_market_data(),
    )
    
    # Analizar precio
    price_analysis = await engine.analyze_price(context)
    
    # Analizar proveedores
    supplier_analyses = []
    for supplier_id in get_package_suppliers(package_id):
        analysis = await engine.analyze_supplier(
            context, supplier_id
        )
        supplier_analyses.append(analysis)
    
    return {
        "price_analysis": price_analysis,
        "supplier_analyses": supplier_analyses,
    }
```

### Monitoreo de Métricas
```python
def track_analysis_metrics(analysis_type: str):
    """Decorator para tracking de métricas."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                METRICS["analysis_operations"].labels(
                    analysis_type=analysis_type
                ).inc()
                return result
            finally:
                duration = time.time() - start_time
                METRICS["analysis_processing_time"].observe(
                    duration
                )
        return wrapper
    return decorator
```
