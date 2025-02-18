"""Página de presupuestos."""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, List
import pandas as pd
from fpdf import FPDF
import io

from src.core.budget.storage import BudgetStorage
from src.core.budget.models import Budget
from src.utils.database import Database
from src.utils.monitoring import monitor


def update_budget_status(budget_id: str, new_status: str) -> bool:
    """Actualizar el estado de un presupuesto."""
    try:
        storage = BudgetStorage(Database())
        storage.update_budget_status(budget_id, new_status)
        monitor.log_metric("budget_status_updated", 1, {"status": new_status})
        return True
    except Exception as e:
        st.error(f"Error al actualizar el presupuesto: {str(e)}")
        monitor.log_error(e, {"action": "update_budget_status"})
        return False


def export_budget_to_pdf(budget: Budget) -> Optional[bytes]:
    """Exportar presupuesto a PDF."""
    try:
        pdf = FPDF()
        pdf.add_page()

        # Título
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, f"Presupuesto #{budget.id}", ln=True, align="C")
        pdf.ln(10)

        # Información del cliente
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Información del Cliente", ln=True)
        pdf.set_font("Arial", "", 12)
        pdf.cell(
            0, 10, f"Cliente: {budget.customer_name or 'Sin especificar'}", ln=True
        )
        pdf.cell(0, 10, f"Fecha: {budget.created_at.strftime('%d/%m/%Y')}", ln=True)
        pdf.cell(
            0, 10, f"Válido hasta: {budget.valid_until.strftime('%d/%m/%Y')}", ln=True
        )
        pdf.ln(10)

        # Detalles del viaje
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Detalles del Viaje", ln=True)
        pdf.set_font("Arial", "", 12)

        for item in budget.items:
            details = item.details
            pdf.cell(
                0,
                10,
                f"Vuelo: {details.get('flight_details', {}).get('flight_number', 'N/A')}",
                ln=True,
            )
            pdf.cell(
                0,
                10,
                f"Aerolínea: {details.get('flight_details', {}).get('airline', 'N/A')}",
                ln=True,
            )
            pdf.cell(
                0,
                10,
                f"Fecha ida: {details.get('departure_date').strftime('%d/%m/%Y %H:%M')}",
                ln=True,
            )
            if details.get("return_date"):
                pdf.cell(
                    0,
                    10,
                    f"Fecha vuelta: {details.get('return_date').strftime('%d/%m/%Y %H:%M')}",
                    ln=True,
                )
            pdf.cell(
                0,
                10,
                f"Clase: {details.get('flight_details', {}).get('cabin_class', 'N/A')}",
                ln=True,
            )
            pdf.cell(
                0,
                10,
                f"Equipaje: {details.get('flight_details', {}).get('baggage', 'N/A')}",
                ln=True,
            )
            pdf.cell(
                0,
                10,
                f"Precio por pasajero: ${item.unit_price} {item.currency}",
                ln=True,
            )
            pdf.cell(0, 10, f"Total: ${item.total_price} {item.currency}", ln=True)
            pdf.ln(5)

        # Notas
        if budget.notes:
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Notas", ln=True)
            pdf.set_font("Arial", "", 12)
            pdf.multi_cell(0, 10, budget.notes)

        return pdf.output(dest="S").encode("latin1")
    except Exception as e:
        st.error(f"Error al exportar a PDF: {str(e)}")
        monitor.log_error(e, {"action": "export_budget_pdf"})
        return None


def filter_budgets(budgets: List[Budget], filters: dict) -> List[Budget]:
    """Filtrar presupuestos según criterios."""
    filtered = budgets

    if filters.get("customer"):
        filtered = [
            b
            for b in filtered
            if filters["customer"].lower() in (b.customer_name or "").lower()
        ]

    if filters.get("status"):
        filtered = [b for b in filtered if b.status == filters["status"]]

    if filters.get("date_range"):
        start_date, end_date = filters["date_range"]
        filtered = [
            b for b in filtered if start_date <= b.created_at.date() <= end_date
        ]

    return filtered


def show_budget_details(budget: Budget, is_selected: bool = False):
    """Mostrar detalles de un presupuesto."""
    # Container principal
    with st.container():
        # Título y estado
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.subheader(f"Presupuesto #{budget.id}")
        with col2:
            st.caption(f"Creado: {budget.created_at.strftime('%d/%m/%Y')}")
        with col3:
            status_colors = {
                "draft": "🟡 Borrador",
                "accepted": "🟢 Aceptado",
                "rejected": "🔴 Rechazado",
            }
            st.write(status_colors.get(budget.status, "Estado desconocido"))

        # Datos del cliente y fechas
        col1, col2 = st.columns(2)
        with col1:
            if not budget.customer_name and is_selected:
                with st.form(key=f"customer_form_{budget.id}"):
                    customer_name = st.text_input("Nombre del Cliente")
                    if st.form_submit_button("Guardar"):
                        if customer_name:
                            budget.customer_name = customer_name
                            BudgetStorage(Database()).update_budget(budget)
                            monitor.log_metric("budget_customer_updated", 1)
                            st.rerun()
            else:
                st.write(f"**Cliente:** {budget.customer_name or 'Sin especificar'}")

        with col2:
            st.write(f"**Válido hasta:** {budget.valid_until.strftime('%d/%m/%Y')}")

        # Detalles del viaje
        for item in budget.items:
            with st.expander("Detalles del Viaje", expanded=is_selected):
                col1, col2 = st.columns(2)
                with col1:
                    details = item.details.get("flight_details", {})
                    st.write(f"**Vuelo:** {details.get('flight_number', 'N/A')}")
                    st.write(f"**Aerolínea:** {details.get('airline', 'N/A')}")
                    st.write(f"**Clase:** {details.get('cabin_class', 'N/A')}")
                    st.write(f"**Equipaje:** {details.get('baggage', 'N/A')}")

                with col2:
                    st.write(f"**Origen:** {item.description.split(' - ')[0]}")
                    st.write(f"**Destino:** {item.description.split(' - ')[1]}")
                    st.write(
                        f"**Fecha ida:** {item.details['departure_date'].strftime('%d/%m/%Y %H:%M')}"
                    )
                    if item.details.get("return_date"):
                        st.write(
                            f"**Fecha vuelta:** {item.details['return_date'].strftime('%d/%m/%Y %H:%M')}"
                        )

        # Precios
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "Precio por pasajero",
                    f"${budget.items[0].unit_price} {budget.items[0].currency}",
                )
            with col2:
                total = sum(item.total_price for item in budget.items)
                st.metric("Total", f"${total} {budget.items[0].currency}")

        # Acciones
        if is_selected:
            st.markdown("---")
            col1, col2, col3 = st.columns(3)

            # Botones de estado
            if budget.status == "draft":
                with col1:
                    if st.button(
                        "✅ Aceptar", key=f"accept_{budget.id}", type="primary"
                    ):
                        if update_budget_status(budget.id, "accepted"):
                            st.success("¡Presupuesto aceptado!")
                            st.rerun()
                with col2:
                    if st.button("❌ Rechazar", key=f"reject_{budget.id}"):
                        if update_budget_status(budget.id, "rejected"):
                            st.error("Presupuesto rechazado")
                            st.rerun()

            # Exportar
            with col3:
                pdf_data = export_budget_to_pdf(budget)
                if pdf_data:
                    st.download_button(
                        "📥 Descargar PDF",
                        pdf_data,
                        f"presupuesto_{budget.id}.pdf",
                        "application/pdf",
                        use_container_width=True,
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
    render_budgets_page()
