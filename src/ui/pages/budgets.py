"""Página de presupuestos con asistencia al vendedor."""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import pandas as pd
from fpdf import FPDF
import io

from src.core.budget.storage import BudgetStorage
from src.core.budget.models import Budget
from src.core.budget.suggestions import SuggestionEngine
from src.core.budget.analysis import BudgetAnalyzer
from src.utils.database import Database
from src.utils.monitoring import monitor
from decimal import Decimal


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


def get_real_time_suggestions(budget: Budget) -> Dict[str, List[str]]:
    """Obtener sugerencias en tiempo real basadas en el presupuesto actual."""
    suggestion_engine = SuggestionEngine()
    return suggestion_engine.get_suggestions(budget)


def analyze_budget_competitiveness(budget: Budget) -> Dict[str, any]:
    """Analizar la competitividad del presupuesto."""
    analyzer = BudgetAnalyzer()
    return analyzer.analyze_competitiveness(budget)


def show_budget_details(budget: Budget, is_selected: bool = False):
    """Mostrar detalles de un presupuesto con asistencia al vendedor."""
    with st.expander("📋 Detalles del Presupuesto", expanded=is_selected):
        # Información básica
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("🆔 ID:", budget.id)
        with col2:
            st.write("👤 Cliente:", budget.customer_name or "Sin especificar")
        with col3:
            st.write("📅 Creado:", budget.created_at.strftime("%d/%m/%Y"))

        # Necesidades del Cliente
        with st.expander("👥 Necesidades del Cliente", expanded=True):
            # Preferencias principales
            st.write("🎯 Preferencias Principales")
            preferences_col1, preferences_col2 = st.columns(2)
            
            with preferences_col1:
                budget.preferences = budget.preferences or {}
                
                # Presupuesto máximo
                max_budget = st.number_input(
                    "💰 Presupuesto Máximo",
                    value=float(budget.preferences.get("max_budget", 0)),
                    step=100.0,
                    key=f"max_budget_{budget.id}"
                )
                budget.preferences["max_budget"] = max_budget
                
                # Flexibilidad de fechas
                date_flexibility = st.select_slider(
                    "📅 Flexibilidad de Fechas",
                    options=["Ninguna", "±1 día", "±2 días", "±3 días", "±1 semana"],
                    value=budget.preferences.get("date_flexibility", "Ninguna"),
                    key=f"date_flex_{budget.id}"
                )
                budget.preferences["date_flexibility"] = date_flexibility

            with preferences_col2:
                # Prioridad del cliente
                priority = st.radio(
                    "🎯 Prioridad del Cliente",
                    options=["Mejor precio", "Mejor horario", "Mejor aerolínea"],
                    index=["Mejor precio", "Mejor horario", "Mejor aerolínea"].index(
                        budget.preferences.get("priority", "Mejor precio")
                    ),
                    key=f"priority_{budget.id}"
                )
                budget.preferences["priority"] = priority
                
                # Servicios adicionales
                services = st.multiselect(
                    "✨ Servicios Adicionales",
                    options=["Seguro de viaje", "Traslados", "Excursiones", "Alquiler de auto"],
                    default=budget.preferences.get("additional_services", []),
                    key=f"services_{budget.id}"
                )
                budget.preferences["additional_services"] = services

            # Notas específicas
            notes = st.text_area(
                "📝 Notas Específicas",
                value=budget.preferences.get("notes", ""),
                key=f"notes_{budget.id}"
            )
            budget.preferences["notes"] = notes

            # Guardar cambios en preferencias
            if st.button("💾 Guardar Preferencias", key=f"save_pref_{budget.id}"):
                try:
                    storage = BudgetStorage(Database())
                    storage.update_budget(budget)
                    st.success("Preferencias guardadas correctamente")
                    # Actualizar sugerencias basadas en nuevas preferencias
                    suggestions = get_real_time_suggestions(budget)
                except Exception as e:
                    st.error(f"Error al guardar preferencias: {str(e)}")

        # Asistente en tiempo real (ahora con sugerencias basadas en preferencias)
        with st.expander("🤖 Asistente en Tiempo Real", expanded=True):
            suggestions = get_real_time_suggestions(budget)
            
            # Sugerencias basadas en preferencias
            if budget.preferences.get("max_budget"):
                total_price = sum(item.total_price for item in budget.items)
                if total_price > budget.preferences["max_budget"]:
                    st.warning(f"⚠️ El presupuesto actual (${total_price}) excede el máximo establecido (${budget.preferences['max_budget']})")
                    if suggestions.get("optimizations"):
                        st.info("💡 Opciones para reducir el presupuesto:")
                        for opt in suggestions["optimizations"]:
                            st.write(f"- {opt}")

            # Resto de sugerencias...
            if suggestions.get("optimizations"):
                st.write("💡 Sugerencias de Optimización:")
                for suggestion in suggestions["optimizations"]:
                    st.info(suggestion)
            
            # Alertas y advertencias
            if suggestions.get("warnings"):
                st.write("⚠️ Puntos de Atención:")
                for warning in suggestions["warnings"]:
                    st.warning(warning)
            
            # Oportunidades
            if suggestions.get("opportunities"):
                st.write("🎯 Oportunidades:")
                for opportunity in suggestions["opportunities"]:
                    st.success(opportunity)

        # Análisis de competitividad
        with st.expander("📊 Análisis de Competitividad"):
            analysis = analyze_budget_competitiveness(budget)
            
            # Mostrar métricas clave
            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            with metrics_col1:
                st.metric(
                    "Precio vs Mercado",
                    f"{analysis['price_difference']}%",
                    delta=analysis['price_trend']
                )
            with metrics_col2:
                st.metric(
                    "Margen Estimado",
                    f"{analysis['estimated_margin']}%",
                    delta=analysis['margin_trend']
                )
            with metrics_col3:
                st.metric(
                    "Score Competitivo",
                    analysis['competitive_score'],
                    delta=analysis['score_trend']
                )

        # Detalles del viaje con comparativas y ajustes
        st.write("✈️ Detalles del Viaje")
        for i, item in enumerate(budget.items):
            with st.expander(f"{item.type.title()} - {item.description}", expanded=True):
                # Ajustes del ítem
                adjust_col1, adjust_col2 = st.columns(2)
                with adjust_col1:
                    # Permitir ajustar precio
                    new_price = st.number_input(
                        "💰 Precio",
                        value=float(item.unit_price),
                        step=10.0,
                        key=f"price_{item.id}"
                    )
                    if new_price != float(item.unit_price):
                        item.unit_price = Decimal(str(new_price))
                        
                    # Permitir ajustar cantidad
                    new_quantity = st.number_input(
                        "🔢 Cantidad",
                        value=item.quantity,
                        min_value=1,
                        step=1,
                        key=f"quantity_{item.id}"
                    )
                    if new_quantity != item.quantity:
                        item.quantity = new_quantity

                with adjust_col2:
                    # Mostrar total actualizado
                    st.write("💵 Total:", f"${item.unit_price * item.quantity} {item.currency}")
                    
                    # Permitir agregar descuentos
                    discount = st.number_input(
                        "🏷️ Descuento (%)",
                        value=float(item.details.get("discount", 0)),
                        min_value=0.0,
                        max_value=100.0,
                        step=5.0,
                        key=f"discount_{item.id}"
                    )
                    if discount > 0:
                        item.details["discount"] = discount
                        discounted_total = item.total_price * (1 - Decimal(str(discount)) / 100)
                        st.write("💰 Total con descuento:", f"${discounted_total} {item.currency}")

                # Detalles específicos según tipo
                if item.type == "flight":
                    flight_col1, flight_col2 = st.columns(2)
                    with flight_col1:
                        # Permitir ajustar clase
                        new_class = st.selectbox(
                            "💺 Clase",
                            options=["Economy", "Premium Economy", "Business", "First"],
                            index=["Economy", "Premium Economy", "Business", "First"].index(
                                item.details.get("flight_details", {}).get("cabin_class", "Economy")
                            ),
                            key=f"class_{item.id}"
                        )
                        if new_class != item.details.get("flight_details", {}).get("cabin_class"):
                            item.details["flight_details"]["cabin_class"] = new_class

                    with flight_col2:
                        # Permitir ajustar equipaje
                        new_baggage = st.selectbox(
                            "🧳 Equipaje",
                            options=["Sin equipaje", "Equipaje de mano", "23kg", "32kg"],
                            index=["Sin equipaje", "Equipaje de mano", "23kg", "32kg"].index(
                                item.details.get("flight_details", {}).get("baggage", "23kg")
                            ),
                            key=f"baggage_{item.id}"
                        )
                        if new_baggage != item.details.get("flight_details", {}).get("baggage"):
                            item.details["flight_details"]["baggage"] = new_baggage

                # Botón para guardar cambios del ítem
                if st.button("💾 Guardar Cambios", key=f"save_item_{item.id}"):
                    try:
                        storage = BudgetStorage(Database())
                        storage.update_budget(budget)
                        st.success("Cambios guardados correctamente")
                    except Exception as e:
                        st.error(f"Error al guardar cambios: {str(e)}")

        # Acciones del presupuesto
        action_col1, action_col2, action_col3, action_col4 = st.columns(4)
        with action_col1:
            if st.button("💾 Guardar", key=f"save_{budget.id}"):
                if update_budget_status(budget.id, "saved"):
                    st.success("Presupuesto guardado")
        with action_col2:
            if st.button("📤 Exportar PDF", key=f"export_{budget.id}"):
                pdf_bytes = export_budget_to_pdf(budget)
                if pdf_bytes:
                    st.download_button(
                        "⬇️ Descargar PDF",
                        pdf_bytes,
                        f"presupuesto_{budget.id}.pdf",
                        "application/pdf",
                    )
        with action_col3:
            if st.button("✅ Aprobar", key=f"approve_{budget.id}"):
                if update_budget_status(budget.id, "approved"):
                    st.success("Presupuesto aprobado")
        with action_col4:
            if st.button("❌ Rechazar", key=f"reject_{budget.id}"):
                if update_budget_status(budget.id, "rejected"):
                    st.success("Presupuesto rechazado")


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
