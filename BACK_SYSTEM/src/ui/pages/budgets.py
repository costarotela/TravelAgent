"""Página de gestión de presupuestos."""

import streamlit as st
from datetime import datetime

from src.core.budget.storage import BudgetStorage
from src.utils.database import Database


def render_budget_page():
    """Renderizar página de presupuestos."""
    st.title("💰 Gestión de Presupuestos")

    # Obtener presupuestos
    storage = BudgetStorage(Database())
    budgets = storage.get_all()

    if not budgets:
        st.info("No hay presupuestos guardados.")
        return

    # Mostrar presupuestos
    for budget in budgets:
        with st.expander(
            f"Presupuesto #{budget.id} - {budget.customer_name or 'Sin nombre'}"
        ):
            col1, col2 = st.columns(2)

            with col1:
                st.write("**Detalles del presupuesto:**")
                st.write(f"- Cliente: {budget.customer_name or 'Sin nombre'}")
                st.write(f"- Creado: {budget.created_at.strftime('%d/%m/%Y %H:%M')}")
                st.write(f"- Válido hasta: {budget.valid_until.strftime('%d/%m/%Y %H:%M')}")
                st.write(f"- Estado: {budget.status}")

            with col2:
                st.write("**Preferencias:**")
                st.write(f"- Presupuesto máximo: {budget.preferences['max_budget']}")
                st.write(f"- Flexibilidad: {budget.preferences['date_flexibility']}")
                st.write(f"- Prioridad: {budget.preferences['priority']}")

            st.write("**Ítems:**")
            for item in budget.items:
                st.write(
                    f"- {item.description}: "
                    f"{item.quantity} x {item.unit_price} {item.currency} = "
                    f"{item.total_price} {item.currency}"
                )


def render_budgets_page():
    """Renderizar página de presupuestos."""
    st.title("Presupuestos")

    # Inicializar storage
    storage = BudgetStorage(Database())

    # Filtros en sidebar
    with st.sidebar:
        st.subheader("Filtros")

        # Búsqueda por cliente
        customer_search = st.text_input("🔍 Buscar por cliente")

        # Filtro por estado
        status_filter = st.selectbox(
            "Estado", options=["Todos", "Borrador", "Aceptado", "Rechazado"], index=0
        )

        # Filtro por fecha
        date_range = st.date_input(
            "Rango de fechas",
            value=(datetime.now().date() - timedelta(days=30), datetime.now().date()),
        )

        # Aplicar filtros
        filters = {
            "customer": customer_search,
            "status": {
                "Borrador": "draft",
                "Aceptado": "accepted",
                "Rechazado": "rejected",
            }.get(status_filter),
            "date_range": (
                date_range
                if isinstance(date_range, tuple)
                else (date_range, date_range)
            ),
        }

    # Si hay un presupuesto seleccionado, mostrarlo primero
    if "selected_budget_id" in st.session_state and st.session_state.selected_budget_id:
        selected_budget = storage.get_budget(st.session_state.selected_budget_id)
        if selected_budget:
            show_budget_details(selected_budget, is_selected=True)
            st.markdown("---")
        # Limpiar selección después de mostrar
        st.session_state.selected_budget_id = None

    # Obtener y filtrar presupuestos
    all_budgets = storage.get_recent_budgets(
        50
    )  # Aumentamos el límite para mejor filtrado
    filtered_budgets = filter_budgets(all_budgets, filters)

    # Mostrar estadísticas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total", len(filtered_budgets))
    with col2:
        accepted = len([b for b in filtered_budgets if b.status == "accepted"])
        st.metric("Aceptados", accepted)
    with col3:
        conversion = (
            f"{(accepted/len(filtered_budgets)*100):.1f}%" if filtered_budgets else "0%"
        )
        st.metric("Tasa de conversión", conversion)

    # Mostrar presupuestos filtrados
    st.subheader("Presupuestos")

    if not filtered_budgets:
        st.info("No hay presupuestos que coincidan con los filtros.")
        return

    # Mostrar presupuestos en tabla
    for budget in filtered_budgets:
        with st.expander(
            f"#{budget.id} - {budget.customer_name or 'Sin cliente'} - "
            f"{budget.items[0].description} - "
            f"{budget.created_at.strftime('%d/%m/%Y')}"
        ):
            show_budget_details(budget)


if __name__ == "__main__":
    render_budget_page()
    render_budgets_page()
