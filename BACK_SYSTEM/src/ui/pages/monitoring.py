"""Página de monitoreo simple."""

import streamlit as st
from datetime import datetime, timedelta
import plotly.graph_objects as go
import pandas as pd

from src.utils.monitoring import monitor


def render_monitoring_page():
    """Renderizar página de monitoreo."""
    st.title("Monitoreo del Sistema")

    # Tabs para métricas y errores
    tab1, tab2 = st.tabs(["Métricas", "Errores"])

    with tab1:
        st.subheader("Métricas del Sistema")

        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            metric_name = st.selectbox(
                "Métrica", ["search_duration", "budget_generation_time", "all"]
            )
        with col2:
            limit = st.number_input("Límite", min_value=10, value=100)

        # Obtener métricas
        metrics = monitor.get_recent_metrics(
            metric_name if metric_name != "all" else None, limit
        )

        if metrics:
            # Convertir a DataFrame
            df = pd.DataFrame(metrics)
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Gráfico de línea
            fig = go.Figure()

            for name in df["name"].unique():
                metric_data = df[df["name"] == name]
                fig.add_trace(
                    go.Scatter(
                        x=metric_data["timestamp"],
                        y=metric_data["value"],
                        name=name,
                        mode="lines+markers",
                    )
                )

            fig.update_layout(
                title="Métricas en el Tiempo",
                xaxis_title="Fecha/Hora",
                yaxis_title="Valor",
                height=400,
            )

            st.plotly_chart(fig, use_container_width=True)

            # Tabla de métricas
            st.write("**Últimas Métricas**")
            st.dataframe(
                df[["timestamp", "name", "value", "tags"]].sort_values(
                    "timestamp", ascending=False
                )
            )
        else:
            st.info("No hay métricas registradas")

    with tab2:
        st.subheader("Errores del Sistema")

        # Obtener errores
        errors = monitor.get_recent_errors(100)

        if errors:
            # Convertir a DataFrame
            df = pd.DataFrame(errors)
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Agrupar por tipo de error
            error_counts = df["error_type"].value_counts()

            # Gráfico de torta
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=error_counts.index, values=error_counts.values, hole=0.3
                    )
                ]
            )

            fig.update_layout(title="Distribución de Errores", height=400)

            st.plotly_chart(fig, use_container_width=True)

            # Tabla de errores
            st.write("**Últimos Errores**")
            st.dataframe(
                df[["timestamp", "error_type", "message", "context"]].sort_values(
                    "timestamp", ascending=False
                )
            )
        else:
            st.info("No hay errores registrados")
