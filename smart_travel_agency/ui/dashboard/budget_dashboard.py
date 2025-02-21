"""
Dashboard para visualización y gestión de presupuestos.
"""
import streamlit as st
from decimal import Decimal
from typing import List, Dict, Any

from smart_travel_agency.core.budget.builder import BudgetBuilder, BudgetItem, BuilderState

def init_session_state():
    """Inicializa el estado de la sesión si no existe."""
    if 'budget_builder' not in st.session_state:
        st.session_state.budget_builder = BudgetBuilder(vendor_id="default")
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "Resumen"

def render_header():
    """Renderiza el encabezado del dashboard."""
    st.title("Smart Travel Budget Dashboard")
    st.markdown("---")

def render_summary_tab(builder: BudgetBuilder):
    """Renderiza la pestaña de resumen del presupuesto."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Estado del Presupuesto")
        st.info(f"Estado actual: {builder.state}")
        st.metric(
            label="Total Items", 
            value=len(builder.items),
            delta=None
        )
    
    with col2:
        st.subheader("Alertas y Sugerencias")
        if builder.warnings:
            st.warning("\n".join(builder.warnings))
        if builder.errors:
            st.error("\n".join(builder.errors))
        
        suggestions = builder.get_suggestions()
        if suggestions:
            st.info("Sugerencias de optimización:")
            for suggestion in suggestions:
                st.write(f"• {suggestion}")

def render_items_tab(builder: BudgetBuilder):
    """Renderiza la pestaña de items del presupuesto."""
    st.subheader("Items del Presupuesto")
    
    if not builder.items:
        st.info("No hay items en el presupuesto")
        return
    
    for idx, item in enumerate(builder.items):
        with st.expander(f"{item.description} - {item.amount} {item.currency}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Detalles:**")
                st.write(f"• Cantidad: {item.quantity}")
                st.write(f"• Precio unitario: {item.amount/item.quantity}")
            with col2:
                st.write("**Metadata:**")
                for key, value in item.metadata.items():
                    st.write(f"• {key}: {value}")

def render_add_item_form(builder: BudgetBuilder):
    """Renderiza el formulario para agregar items."""
    st.subheader("Agregar Nuevo Item")
    
    with st.form("add_item_form"):
        description = st.text_input("Descripción")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            amount = st.number_input("Monto", min_value=0.0, step=0.01)
        with col2:
            quantity = st.number_input("Cantidad", min_value=1, step=1)
        with col3:
            currency = st.selectbox("Moneda", ["USD", "EUR", "ARS"])
        
        # Metadata básica
        st.subheader("Metadata")
        col1, col2 = st.columns(2)
        with col1:
            provider_id = st.text_input("ID Proveedor")
            category = st.selectbox(
                "Categoría",
                ["accommodation", "transport", "activity", "food", "other"]
            )
        with col2:
            season = st.selectbox("Temporada", ["low", "medium", "high"])
            rating = st.slider("Rating", 1, 5, 3)
        
        submitted = st.form_submit_button("Agregar Item")
        
        if submitted and description and amount > 0:
            new_item = BudgetItem(
                description=description,
                amount=Decimal(str(amount)),
                quantity=quantity,
                currency=currency,
                metadata={
                    "provider_id": provider_id,
                    "category": category,
                    "season": season,
                    "rating": rating
                }
            )
            builder.add_item(new_item)
            st.success("Item agregado exitosamente!")
            st.experimental_rerun()

def main():
    """Función principal del dashboard."""
    init_session_state()
    render_header()
    
    # Tabs principales
    tab1, tab2, tab3 = st.tabs(["Resumen", "Items", "Agregar Item"])
    
    with tab1:
        render_summary_tab(st.session_state.budget_builder)
    
    with tab2:
        render_items_tab(st.session_state.budget_builder)
    
    with tab3:
        render_add_item_form(st.session_state.budget_builder)

if __name__ == "__main__":
    main()
