"""Página de presupuestos."""
import streamlit as st
from datetime import datetime
from typing import Optional

from src.core.budget.storage import BudgetStorage
from src.core.budget.models import Budget
from src.utils.database import Database

def update_budget_status(budget_id: str, new_status: str) -> bool:
    """Actualizar el estado de un presupuesto."""
    try:
        storage = BudgetStorage(Database())
        storage.update_budget_status(budget_id, new_status)
        return True
    except Exception as e:
        st.error(f"Error al actualizar el presupuesto: {str(e)}")
        return False

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
        if budget.status == "draft" and is_selected:
            col1, col2 = st.columns(2)
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
