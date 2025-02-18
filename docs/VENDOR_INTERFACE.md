# Interfaz Interactiva de Vendedor

## Descripción General

La Interfaz Interactiva de Vendedor es una aplicación web implementada con Streamlit que permite a los vendedores:
- Visualizar cambios en tiempo real
- Realizar ajustes manuales a presupuestos
- Comparar diferentes escenarios
- Gestionar clientes y preferencias
- Monitorear métricas de rendimiento

## Arquitectura

### 1. Componentes Principales

#### Modelos (`models.py`)
- `VendorSession`: Datos de sesión del vendedor
- `UIPreferences`: Preferencias de interfaz
- `BudgetScenario`: Escenarios de presupuesto
- `ClientView`: Vista de cliente

#### Aplicación Streamlit (`app.py`)
- Gestión de estado de sesión
- Navegación y routing
- Componentes interactivos
- Visualización de datos

### 2. Vistas Principales

#### Dashboard
- Cambios recientes
- Alertas de precio
- Acciones pendientes
- Métricas de rendimiento

#### Editor de Presupuestos
- Selección de paquetes
- Desglose de precios
- Historial de cambios
- Comparación de escenarios

#### Gestión de Clientes
- Lista de clientes
- Detalles de cliente
- Historial de actividad
- Preferencias

## Características Principales

### 1. Dashboard Interactivo
```python
def render_dashboard():
    """Render dashboard view."""
    st.title("Dashboard")
    
    # Recent Changes
    st.subheader("Recent Changes")
    changes_df = pd.DataFrame(...)
    st.dataframe(changes_df)
    
    # Price Alerts
    st.subheader("Price Alerts")
    fig = px.bar(...)
    st.plotly_chart(fig)
```

### 2. Editor de Presupuestos
```python
def render_budget_editor():
    """Render budget editor view."""
    tab1, tab2, tab3, tab4 = st.tabs([
        "Packages",
        "Price Breakdown",
        "Change History",
        "Scenarios"
    ])
```

### 3. Gestión de Escenarios
```python
# Visualización de escenarios
scenarios_df = pd.DataFrame({
    "Scenario": ["Base", "High Season", "Promo"],
    "Total Price": [5600, 6200, 5100],
    "Margin": ["15%", "20%", "12%"]
})
st.dataframe(scenarios_df)
```

## Integración con Otros Sistemas

### 1. Con el Sistema de Preferencias
- Aplicación de preferencias de usuario
- Filtros personalizados
- Reglas de vendedor

### 2. Con el Motor de Presupuestos
- Actualización en tiempo real
- Versionado de cambios
- Escenarios comparativos

### 3. Con el Sistema de Recolección
- Alertas de cambios de precio
- Disponibilidad en tiempo real
- Alternativas sugeridas

## Monitoreo y Métricas

- Métricas de rendimiento
- Gráficos interactivos con Plotly
- Análisis de tendencias
- KPIs de vendedor

## Próximas Mejoras

1. **Análisis Predictivo**
   - Predicción de cambios de precio
   - Recomendaciones automáticas
   - Optimización de márgenes

2. **Colaboración en Tiempo Real**
   - Notas compartidas
   - Historial de comunicaciones
   - Seguimiento de cambios

3. **Personalización Avanzada**
   - Widgets configurables
   - Layouts personalizados
   - Filtros avanzados

4. **Optimizaciones**
   - Caché de datos
   - Actualizaciones incrementales
   - Compresión de datos
