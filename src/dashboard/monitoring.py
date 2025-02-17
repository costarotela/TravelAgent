"""Dashboard de monitoreo para la aplicación."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
from typing import Dict, List, Any

from src.utils.monitoring import get_metrics_db_path

def load_metrics(days: int = 7) -> pd.DataFrame:
    """Cargar métricas de la base de datos."""
    conn = sqlite3.connect(get_metrics_db_path())
    since = datetime.now() - timedelta(days=days)
    
    query = """
    SELECT 
        timestamp,
        metric_name,
        metric_value,
        json_extract(tags, '$.provider') as provider,
        json_extract(tags, '$.action') as action,
        json_extract(tags, '$.total') as total_items
    FROM metrics 
    WHERE timestamp >= ?
    ORDER BY timestamp DESC
    """
    
    df = pd.read_sql_query(query, conn, params=(since.isoformat(),))
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def load_errors(days: int = 7) -> pd.DataFrame:
    """Cargar errores de la base de datos."""
    conn = sqlite3.connect(get_metrics_db_path())
    since = datetime.now() - timedelta(days=days)
    
    query = """
    SELECT 
        timestamp,
        error_type,
        error_message,
        json_extract(tags, '$.provider') as provider,
        json_extract(tags, '$.action') as action
    FROM errors 
    WHERE timestamp >= ?
    ORDER BY timestamp DESC
    """
    
    df = pd.read_sql_query(query, conn, params=(since.isoformat(),))
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def render_metrics_overview(df: pd.DataFrame):
    """Mostrar resumen de métricas principales."""
    st.subheader("📊 Resumen de Métricas")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Tiempo promedio de búsqueda
    search_times = df[df['metric_name'] == 'search_duration']
    avg_search_time = search_times['metric_value'].mean()
    with col1:
        st.metric(
            "Tiempo Promedio de Búsqueda",
            f"{avg_search_time:.2f}s"
        )
    
    # Tasa de éxito del caché
    cache_hits = df[df['metric_name'] == 'cache_hit']['metric_value'].sum()
    total_searches = len(search_times)
    cache_rate = (cache_hits / total_searches * 100) if total_searches > 0 else 0
    with col2:
        st.metric(
            "Tasa de Caché",
            f"{cache_rate:.1f}%"
        )
    
    # Resultados promedio por búsqueda
    results_df = df[df['metric_name'] == 'total_results']
    avg_results = results_df['metric_value'].mean()
    with col3:
        st.metric(
            "Resultados Promedio",
            f"{avg_results:.0f}"
        )
    
    # Errores totales
    errors_df = df[df['metric_name'] == 'provider_errors']
    total_errors = errors_df['metric_value'].sum()
    with col4:
        st.metric(
            "Errores Totales",
            f"{total_errors:.0f}"
        )

def render_search_times_chart(df: pd.DataFrame):
    """Mostrar gráfico de tiempos de búsqueda."""
    st.subheader("⏱️ Tiempos de Búsqueda")
    
    search_times = df[df['metric_name'] == 'search_duration'].copy()
    if not search_times.empty:
        fig = px.line(
            search_times,
            x='timestamp',
            y='metric_value',
            title='Tiempos de Búsqueda a lo Largo del Tiempo'
        )
        fig.update_layout(
            xaxis_title="Fecha/Hora",
            yaxis_title="Duración (segundos)"
        )
        st.plotly_chart(fig, use_container_width=True)

def render_provider_stats(df: pd.DataFrame):
    """Mostrar estadísticas por proveedor."""
    st.subheader("🔍 Estadísticas por Proveedor")
    
    provider_stats = df[
        (df['metric_name'].isin(['search_success', 'provider_errors'])) &
        (df['provider'].notna())
    ]
    
    if not provider_stats.empty:
        # Agrupar por proveedor
        stats = provider_stats.groupby(['provider', 'metric_name'])['metric_value'].sum()
        stats = stats.unstack(fill_value=0)
        
        # Calcular tasa de éxito
        total_searches = stats['search_success'] + stats['provider_errors']
        success_rate = (stats['search_success'] / total_searches * 100).round(1)
        
        # Crear tabla
        fig = go.Figure(data=[
            go.Table(
                header=dict(
                    values=['Proveedor', 'Búsquedas Exitosas', 'Errores', 'Tasa de Éxito'],
                    fill_color='paleturquoise',
                    align='left'
                ),
                cells=dict(
                    values=[
                        stats.index,
                        stats['search_success'],
                        stats['provider_errors'],
                        success_rate.map(lambda x: f"{x}%")
                    ],
                    fill_color='lavender',
                    align='left'
                )
            )
        ])
        st.plotly_chart(fig, use_container_width=True)

def render_error_log(errors_df: pd.DataFrame):
    """Mostrar log de errores."""
    st.subheader("❌ Log de Errores")
    
    if not errors_df.empty:
        # Formatear para mostrar
        errors_display = errors_df.copy()
        errors_display['timestamp'] = errors_display['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        st.dataframe(
            errors_display[['timestamp', 'provider', 'action', 'error_type', 'error_message']],
            use_container_width=True
        )
    else:
        st.info("No hay errores registrados en el período seleccionado")

def render_monitoring_dashboard():
    """Renderizar el dashboard completo."""
    st.title("🎯 Dashboard de Monitoreo")
    
    # Selector de período
    days = st.sidebar.slider(
        "Período de Análisis (días)",
        min_value=1,
        max_value=30,
        value=7
    )
    
    # Cargar datos
    with st.spinner("Cargando métricas..."):
        metrics_df = load_metrics(days)
        errors_df = load_errors(days)
    
    if metrics_df.empty:
        st.warning("No hay datos de métricas para mostrar")
        return
    
    # Renderizar secciones
    render_metrics_overview(metrics_df)
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        render_search_times_chart(metrics_df)
    with col2:
        render_provider_stats(metrics_df)
    
    st.divider()
    render_error_log(errors_df)

if __name__ == "__main__":
    render_monitoring_dashboard()
