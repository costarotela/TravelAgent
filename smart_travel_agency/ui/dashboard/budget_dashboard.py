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

def categorize_suggestions(suggestions: List[str]) -> Dict[str, List[str]]:
    """
    Categoriza las sugerencias por tipo.
    
    Args:
        suggestions: Lista de sugerencias
        
    Returns:
        Diccionario con sugerencias categorizadas
    """
    categorized = {
        " Optimización de Costos": [],
        " Temporada": [],
        " Paquetes": []
    }
    
    for suggestion in suggestions:
        if "económic" in suggestion.lower() or "precio" in suggestion.lower():
            categorized[" Optimización de Costos"].append(suggestion)
        elif "tempor" in suggestion.lower() or "temporada" in suggestion.lower():
            categorized[" Temporada"].append(suggestion)
        elif "paquete" in suggestion.lower():
            categorized[" Paquetes"].append(suggestion)
    
    return {k: v for k, v in categorized.items() if v}

def render_suggestions(builder: BudgetBuilder):
    """Renderiza las sugerencias de manera organizada."""
    suggestions = builder.get_suggestions()
    if not suggestions:
        return
    
    st.subheader(" Sugerencias de Optimización")
    
    categorized = categorize_suggestions(suggestions)
    for category, items in categorized.items():
        with st.expander(f"{category} ({len(items)})"):
            for idx, item in enumerate(items):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.info(item)
                with col2:
                    button_key = f"{category}_{idx}"
                    if "económic" in item.lower():
                        st.button("Ver Alternativa", key=f"btn_alt_{button_key}")
                    elif "temporada" in item.lower():
                        st.button("Cambiar Fecha", key=f"btn_date_{button_key}")
                    elif "paquete" in item.lower():
                        st.button("Ver Paquete", key=f"btn_pkg_{button_key}")

def render_summary_tab(builder: BudgetBuilder):
    """Renderiza la pestaña de resumen del presupuesto."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(" Estado del Presupuesto")
        st.info(f"Estado actual: {builder.state}")
        
        # Métricas principales
        total_amount = sum(item.amount * item.quantity for item in builder.items)
        st.metric(
            label="Total Items", 
            value=len(builder.items),
            delta=None
        )
        if builder.items:
            st.metric(
                label="Monto Total",
                value=f"${total_amount:,.2f}",
                delta=None
            )
    
    with col2:
        st.subheader(" Alertas")
        if builder.warnings:
            for warning in builder.warnings:
                st.warning(warning)
        if builder.errors:
            for error in builder.errors:
                st.error(error)
        
        # Renderizar sugerencias en su propia sección
        render_suggestions(builder)

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
            st.rerun()

def add_example_items(builder: BudgetBuilder):
    """Agrega items de ejemplo al presupuesto."""
    items = [
        BudgetItem(
            description="Hotel de Lujo en Cancún",
            amount=Decimal("1500"),
            quantity=1,
            currency="USD",
            metadata={
                "provider_id": "hotel_provider1",
                "category": "accommodation",
                "season": "high",
                "rating": 5
            }
        ),
        BudgetItem(
            description="Tour a Chichen Itzá",
            amount=Decimal("120"),
            quantity=2,
            currency="USD",
            metadata={
                "provider_id": "tour_provider1",
                "category": "activity",
                "season": "medium",
                "rating": 4
            }
        ),
        BudgetItem(
            description="Tour a Xcaret",
            amount=Decimal("150"),
            quantity=2,
            currency="USD",
            metadata={
                "provider_id": "tour_provider1",
                "category": "activity",
                "season": "high",
                "rating": 5
            }
        )
    ]
    
    for item in items:
        builder.add_item(item)

def main():
    """Función principal del dashboard."""
    init_session_state()
    render_header()
    
    # Botón para agregar items de ejemplo
    if not st.session_state.budget_builder.items:
        if st.button(" Cargar Items de Ejemplo"):
            add_example_items(st.session_state.budget_builder)
            st.rerun()
    
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
