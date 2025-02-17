"""Página de presupuestos."""
import streamlit as st
from datetime import datetime
from typing import Optional
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
        pdf.cell(0, 10, f"Cliente: {budget.customer_name or 'Sin especificar'}", ln=True)
        pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
        pdf.ln(10)
        
        # Detalles del viaje
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Detalles del Viaje", ln=True)
        pdf.set_font("Arial", "", 12)
        
        for item in budget.items:
            pdf.cell(0, 10, f"Origen: {item.description.split(' → ')[0]}", ln=True)
            pdf.cell(0, 10, f"Destino: {item.description.split(' → ')[1]}", ln=True)
            pdf.cell(0, 10, f"Fecha: {item.details.get('departure_date', 'N/A')}", ln=True)
            pdf.cell(0, 10, f"Pasajeros: {item.details.get('adults', 0)} adultos", ln=True)
            pdf.cell(0, 10, f"Precio: ${item.total_price} {item.currency}", ln=True)
            pdf.ln(5)
        
        # Total
        pdf.set_font("Arial", "B", 12)
        total = sum(item.total_price for item in budget.items)
        pdf.cell(0, 10, f"Total: ${total} {budget.items[0].currency}", ln=True)
        
        return pdf.output(dest="S").encode("latin1")
    except Exception as e:
        st.error(f"Error al exportar a PDF: {str(e)}")
        monitor.log_error(e, {"action": "export_budget_pdf"})
        return None

def export_budget_to_excel(budget: Budget) -> Optional[bytes]:
    """Exportar presupuesto a Excel."""
    try:
        # Crear DataFrame con los items
        data = []
        for item in budget.items:
            data.append({
                "Tipo": item.type,
                "Descripción": item.description,
                "Precio": item.total_price,
                "Moneda": item.currency,
                "Fecha": item.details.get("departure_date", "N/A"),
                "Pasajeros": item.details.get("adults", 0)
            })
        
        df = pd.DataFrame(data)
        
        # Crear buffer en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Presupuesto")
        
        return output.getvalue()
    except Exception as e:
        st.error(f"Error al exportar a Excel: {str(e)}")
        monitor.log_error(e, {"action": "export_budget_excel"})
        return None

def show_budget_details(budget: Budget, is_selected: bool = False):
    """Mostrar detalles de un presupuesto."""
    # Container principal
    with st.container():
        # Título y estado
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"Presupuesto #{budget.id}")
        with col2:
            if budget.status == "draft":
                st.info("📝 Borrador")
            elif budget.status == "accepted":
                st.success("✅ Aceptado")
            else:
                st.error("❌ Rechazado")
        
        # Datos del cliente
        if not budget.customer_name and is_selected:
            with st.form(key=f"customer_form_{budget.id}"):
                customer_name = st.text_input("Nombre del Cliente")
                if st.form_submit_button("Guardar"):
                    if customer_name:
                        budget.customer_name = customer_name
                        BudgetStorage(Database()).update_budget(budget)
                        monitor.log_metric("budget_customer_updated", 1)
                        st.rerun()
        elif budget.customer_name:
            st.write(f"**Cliente:** {budget.customer_name}")
        
        # Detalles del vuelo
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Detalles del Vuelo**")
            st.write(f"Origen: {budget.items[0].description.split(' → ')[0]}")
            st.write(f"Destino: {budget.items[0].description.split(' → ')[1]}")
            st.write(f"Fecha: {budget.items[0].details.get('departure_date', 'N/A')}")
        
        with col2:
            st.write("**Pasajeros y Precio**")
            st.write(f"Adultos: {budget.items[0].details.get('adults', 0)}")
            total = sum(item.total_price for item in budget.items)
            st.write(f"**Total:** ${total} {budget.items[0].currency}")
        
        # Acciones
        if is_selected:
            col1, col2, col3 = st.columns(3)
            
            # Botones de estado
            if budget.status == "draft":
                with col1:
                    if st.button("✅ Aceptar", key=f"accept_{budget.id}"):
                        if update_budget_status(budget.id, "accepted"):
                            st.success("¡Presupuesto aceptado!")
                            st.rerun()
                with col2:
                    if st.button("❌ Rechazar", key=f"reject_{budget.id}"):
                        if update_budget_status(budget.id, "rejected"):
                            st.error("Presupuesto rechazado")
                            st.rerun()
            
            # Botones de exportación
            with col3:
                export_format = st.selectbox(
                    "Formato",
                    options=["PDF", "Excel"],
                    key=f"export_{budget.id}"
                )
                
                if export_format == "PDF":
                    pdf_data = export_budget_to_pdf(budget)
                    if pdf_data:
                        st.download_button(
                            "📥 Descargar PDF",
                            pdf_data,
                            f"presupuesto_{budget.id}.pdf",
                            "application/pdf"
                        )
                else:
                    excel_data = export_budget_to_excel(budget)
                    if excel_data:
                        st.download_button(
                            "📥 Descargar Excel",
                            excel_data,
                            f"presupuesto_{budget.id}.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

def render_budgets_page():
    """Renderizar página de presupuestos."""
    st.title("Presupuestos")
    
    # Obtener presupuestos
    storage = BudgetStorage(Database())
    
    # Si hay un presupuesto seleccionado, mostrarlo primero
    if st.session_state.selected_budget_id:
        selected_budget = storage.get_budget(st.session_state.selected_budget_id)
        if selected_budget:
            show_budget_details(selected_budget, is_selected=True)
            st.markdown("---")
        # Limpiar selección después de mostrar
        st.session_state.selected_budget_id = None
    
    # Mostrar lista de presupuestos recientes
    st.subheader("Presupuestos Recientes")
    budgets = storage.get_recent_budgets(5)
    
    if not budgets:
        st.info("No hay presupuestos disponibles.")
        return
    
    # Mostrar presupuestos en expansores
    for budget in budgets:
        with st.expander(
            f"Presupuesto #{budget.id} - {budget.items[0].description}"
        ):
            show_budget_details(budget)

if __name__ == "__main__":
    render_budgets_page()
