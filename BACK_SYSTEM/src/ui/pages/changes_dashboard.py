import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List
import plotly.graph_objects as go

from ...core.providers.ola_models import PaqueteOLA


def render_changes_dashboard(changes: Dict[str, List[PaqueteOLA]]):
    """
    Renderiza el dashboard de cambios.

    Args:
        changes: Diccionario con los cambios detectados
    """
    st.title("🔄 Monitor de Cambios")

    # Resumen de cambios
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Nuevos Paquetes", len(changes.get("nuevos", [])), delta=None)

    with col2:
        st.metric(
            "Paquetes Actualizados", len(changes.get("actualizados", [])), delta=None
        )

    with col3:
        st.metric("Paquetes Eliminados", len(changes.get("eliminados", [])), delta=None)

    # Detalles de cambios
    if changes.get("actualizados"):
        st.subheader("📊 Cambios en Precios")

        # Preparar datos para el gráfico
        price_changes = []
        for pkg in changes["actualizados"]:
            if hasattr(pkg, "precio_anterior"):
                price_changes.append(
                    {
                        "id": pkg.id,
                        "destino": pkg.destino,
                        "precio_anterior": float(pkg.precio_anterior),
                        "precio_actual": float(pkg.precio),
                        "cambio": float(pkg.precio) - float(pkg.precio_anterior),
                    }
                )

        if price_changes:
            df = pd.DataFrame(price_changes)

            # Gráfico de cambios de precio
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=df["destino"],
                    y=df["cambio"],
                    name="Cambio en Precio",
                    marker_color=["red" if x < 0 else "green" for x in df["cambio"]],
                )
            )

            fig.update_layout(
                title="Cambios en Precios por Destino",
                xaxis_title="Destino",
                yaxis_title="Cambio en Precio ($)",
                showlegend=False,
            )

            st.plotly_chart(fig)

            # Tabla de cambios
            st.subheader("📋 Detalles de Cambios")
            st.dataframe(
                df[
                    ["destino", "precio_anterior", "precio_actual", "cambio"]
                ].style.format(
                    {
                        "precio_anterior": "${:,.2f}",
                        "precio_actual": "${:,.2f}",
                        "cambio": "${:,.2f}",
                    }
                )
            )

    # Nuevos paquetes
    if changes.get("nuevos"):
        st.subheader("🆕 Nuevos Paquetes")
        for pkg in changes["nuevos"]:
            with st.expander(f"{pkg.destino} - ${pkg.precio:,.2f}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Detalles:**")
                    st.write(f"- ID: {pkg.id}")
                    st.write(f"- Destino: {pkg.destino}")
                    st.write(f"- Precio: ${pkg.precio:,.2f}")
                with col2:
                    st.write("**Fechas disponibles:**")
                    for fecha in pkg.fechas:
                        st.write(f"- {fecha.strftime('%d/%m/%Y')}")

    # Paquetes eliminados
    if changes.get("eliminados"):
        st.subheader("❌ Paquetes Eliminados")
        for pkg in changes["eliminados"]:
            st.error(f"Paquete eliminado: {pkg.destino} " f"(ID: {pkg.id})")


def render_settings():
    """Renderiza la configuración del monitor de cambios."""
    st.sidebar.title("⚙️ Configuración")

    # Intervalo de actualización
    update_interval = st.sidebar.slider(
        "Intervalo de actualización (segundos)",
        min_value=60,
        max_value=3600,
        value=300,
        step=60,
    )

    # Tolerancia de precios
    price_tolerance = st.sidebar.slider(
        "Tolerancia de precios (%)",
        min_value=0.01,
        max_value=5.0,
        value=0.01,
        step=0.01,
    )

    # Notificaciones
    st.sidebar.subheader("🔔 Notificaciones")
    notify_new = st.sidebar.checkbox("Nuevos paquetes", value=True)
    notify_updates = st.sidebar.checkbox("Actualizaciones", value=True)
    notify_deletes = st.sidebar.checkbox("Eliminaciones", value=True)

    return {
        "update_interval": update_interval,
        "price_tolerance": price_tolerance,
        "notifications": {
            "new": notify_new,
            "updates": notify_updates,
            "deletes": notify_deletes,
        },
    }
