"""Página de inicio de la aplicación."""

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

from src.core.budget.storage import BudgetStorage
from src.utils.database import Database
from src.utils.monitoring import monitor


def get_recent_activity():
    """Obtener actividad reciente del sistema."""
    try:
        storage = BudgetStorage(Database())
        recent_budgets = storage.get_recent_budgets(limit=5)

        if not recent_budgets:
            return None

        # Convertir a DataFrame para mejor visualización
        data = []
        for budget in recent_budgets:
            data.append(
                {
                    "ID": budget.id,
                    "Cliente": budget.customer_name,
                    "Fecha": budget.created_at.strftime("%d/%m/%Y"),
                    "Estado": budget.status.capitalize(),
                    "Total": f"${budget.total_amount['USD']:.2f}",
                }
            )

        return pd.DataFrame(data)
    except Exception as e:
        monitor.log_error(e, {"action": "get_recent_activity"})
        return None


def get_quick_stats():
    """Obtener estadísticas rápidas."""
    try:
        storage = BudgetStorage(Database())

        # Obtener datos
        total_budgets = storage.count_budgets()
        accepted_budgets = storage.count_budgets(status="accepted")
        pending_budgets = storage.count_budgets(status="pending")

        # Calcular tasa de conversión
        conversion_rate = (
            (accepted_budgets / total_budgets * 100) if total_budgets > 0 else 0
        )

        return {
            "total": total_budgets,
            "accepted": accepted_budgets,
            "pending": pending_budgets,
            "conversion": conversion_rate,
        }
    except Exception as e:
        monitor.log_error(e, {"action": "get_quick_stats"})
        return None


def render_quick_search():
    """Renderizar búsqueda rápida."""
    st.subheader("🔍 Búsqueda Rápida")

    with st.form(key="quick_search", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            origin = st.text_input("Origen", value="Buenos Aires")
            date = st.date_input(
                "Fecha de Viaje",
                value=datetime.now().date() + timedelta(days=7),
                min_value=datetime.now().date(),
            )

        with col2:
            destination = st.text_input("Destino")
            passengers = st.number_input("Pasajeros", min_value=1, value=1)

        if st.form_submit_button(
            "Buscar Vuelos", use_container_width=True, type="primary"
        ):
            # Guardar parámetros en sesión
            st.session_state.search_params = {
                "origin": origin,
                "destination": destination,
                "date": date,
                "passengers": passengers,
            }
            # Redireccionar a búsqueda
            st.session_state.redirect_to = "Búsqueda"


def render_home_page():
    """Renderizar página de inicio."""
    st.title("Bienvenido a Costa Rotela Travel")

    # Búsqueda rápida
    render_quick_search()

    # Estadísticas rápidas
    stats = get_quick_stats()
    if stats:
        st.subheader("📊 Resumen")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Presupuestos", stats["total"])

        with col2:
            st.metric("Aceptados", stats["accepted"])

        with col3:
            st.metric("Pendientes", stats["pending"])

        with col4:
            st.metric("Tasa Conversión", f"{stats['conversion']:.1f}%")

    # Actividad reciente
    st.subheader("📋 Actividad Reciente")
    recent_data = get_recent_activity()

    if recent_data is not None:
        st.dataframe(
            recent_data,
            column_config={
                "ID": st.column_config.TextColumn(width=100),
                "Cliente": st.column_config.TextColumn(width=150),
                "Fecha": st.column_config.TextColumn(width=100),
                "Estado": st.column_config.TextColumn(width=100),
                "Total": st.column_config.TextColumn(width=100),
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No hay actividad reciente para mostrar.")

    # Enlaces rápidos
    st.subheader("🔗 Enlaces Rápidos")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 Ver Presupuestos", use_container_width=True):
            st.session_state.redirect_to = "Presupuestos"

    with col2:
        if st.button("✈️ Nueva Búsqueda", use_container_width=True):
            st.session_state.redirect_to = "Búsqueda"


if __name__ == "__main__":
    render_home_page()
