"""
Dashboard para visualización y gestión de presupuestos.
"""
import streamlit as st
from decimal import Decimal
from typing import List, Dict, Any
from datetime import datetime

from smart_travel_agency.core.budget.builder import BudgetBuilder, BudgetItem
from smart_travel_agency.core.notifications import (
    NotificationType, NotificationSeverity, 
    Notification, NotificationManager
)

def init_session_state():
    """Inicializa el estado de la sesión si no existe."""
    if 'budget_builder' not in st.session_state:
        st.session_state.budget_builder = BudgetBuilder(vendor_id="default")
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "Resumen"
    if 'notification_manager' not in st.session_state:
        st.session_state.notification_manager = NotificationManager()
    if 'show_notification' not in st.session_state:
        st.session_state.show_notification = None

def handle_notification(notification: Notification):
    """Maneja la llegada de una nueva notificación."""
    if notification.severity == NotificationSeverity.HIGH:
        st.session_state.show_notification = notification

def render_notifications():
    """Renderiza las notificaciones emergentes."""
    if st.session_state.show_notification:
        notification = st.session_state.show_notification
        
        # Crear contenedor para la notificación
        with st.container():
            col1, col2 = st.columns([5,1])
            
            with col1:
                if notification.severity == NotificationSeverity.HIGH:
                    st.error(f"⚠️ {notification.message}")
                elif notification.severity == NotificationSeverity.MEDIUM:
                    st.warning(f"📢 {notification.message}")
                else:
                    st.info(f"ℹ️ {notification.message}")
                
                if notification.data:
                    st.write("Detalles:", notification.data)
            
            with col2:
                if st.button("✕", key=f"close_{hash(notification.timestamp)}"):
                    notification.mark_as_read()
                    st.session_state.show_notification = None
                    st.rerun()

def get_notification_counts():
    """Obtiene el conteo de notificaciones por severidad."""
    manager = st.session_state.notification_manager
    unread = manager.get_unread()
    
    return {
        NotificationSeverity.HIGH: len([n for n in unread if n.severity == NotificationSeverity.HIGH]),
        NotificationSeverity.MEDIUM: len([n for n in unread if n.severity == NotificationSeverity.MEDIUM]),
        NotificationSeverity.LOW: len([n for n in unread if n.severity == NotificationSeverity.LOW])
    }

def render_notification_bar():
    """Renderiza la barra superior con contadores de notificaciones."""
    counts = get_notification_counts()
    total = sum(counts.values())
    
    if total > 0:
        st.markdown("---")
        cols = st.columns([1, 1, 1, 3])
        
        with cols[0]:
            if counts[NotificationSeverity.HIGH] > 0:
                st.error(f"⚠️ Críticas: {counts[NotificationSeverity.HIGH]}")
        
        with cols[1]:
            if counts[NotificationSeverity.MEDIUM] > 0:
                st.warning(f"📢 Importantes: {counts[NotificationSeverity.MEDIUM]}")
        
        with cols[2]:
            if counts[NotificationSeverity.LOW] > 0:
                st.info(f"ℹ️ Informativas: {counts[NotificationSeverity.LOW]}")
        
        with cols[3]:
            if st.button("Ver Todas", key="view_all_notifications"):
                # TODO: Implementar vista detallada de notificaciones
                pass

def render_header():
    """Renderiza el encabezado del dashboard."""
    st.title("Smart Travel Budget Dashboard")
    render_notification_bar()
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

def render_notification_panel():
    """Renderiza el panel lateral con historial de notificaciones."""
    with st.sidebar:
        st.header("📋 Historial de Notificaciones")
        
        # Filtros
        st.subheader("Filtros")
        cols = st.columns(2)
        with cols[0]:
            selected_type = st.selectbox(
                "Tipo",
                options=[t.value for t in NotificationType],
                index=None,
                placeholder="Todos"
            )
        with cols[1]:
            selected_severity = st.selectbox(
                "Severidad",
                options=[s.value for s in NotificationSeverity],
                index=None,
                placeholder="Todas"
            )
        
        show_read = st.checkbox("Mostrar leídas", value=False)
        
        st.markdown("---")
        
        # Obtener y filtrar notificaciones
        notifications = st.session_state.notification_manager.notifications
        
        if not show_read:
            notifications = [n for n in notifications if not n.read]
        
        if selected_type:
            notifications = [n for n in notifications if n.type.value == selected_type]
            
        if selected_severity:
            notifications = [n for n in notifications if n.severity.value == selected_severity]
        
        # Mostrar notificaciones
        if not notifications:
            st.info("No hay notificaciones que mostrar")
        else:
            for notification in sorted(
                notifications,
                key=lambda x: x.timestamp,
                reverse=True
            ):
                with st.expander(
                    f"{'📌' if not notification.read else '✓'} {notification.message}",
                    expanded=not notification.read
                ):
                    st.write(f"**Tipo:** {notification.type.value}")
                    st.write(f"**Severidad:** {notification.severity.value}")
                    st.write(f"**Fecha:** {notification.timestamp.strftime('%Y-%m-%d %H:%M')}")
                    
                    if notification.data:
                        st.write("**Detalles:**")
                        for key, value in notification.data.items():
                            st.write(f"- {key}: {value}")
                    
                    if not notification.read:
                        if st.button("Marcar como leída", key=f"mark_read_{hash(notification.timestamp)}"):
                            notification.mark_as_read()
                            st.rerun()

def main():
    """Función principal del dashboard."""
    init_session_state()
    
    # Suscribir al manejador de notificaciones
    st.session_state.notification_manager.subscribe(handle_notification)
    
    # Renderizar panel lateral
    render_notification_panel()
    
    render_header()
    
    # Renderizar notificaciones emergentes
    render_notifications()
    
    # Ejemplo de notificación (temporal, para pruebas)
    if not st.session_state.budget_builder.items:
        if st.button("📝 Cargar Items de Ejemplo"):
            add_example_items(st.session_state.budget_builder)
            
            # Crear notificaciones de ejemplo
            notifications = [
                Notification(
                    type=NotificationType.PRICE_CHANGE,
                    message="¡Alerta! El precio del Hotel de Lujo en Cancún ha aumentado un 15%",
                    item_id="hotel_123",
                    severity=NotificationSeverity.HIGH,
                    timestamp=datetime.now(),
                    data={
                        "old_price": 1500,
                        "new_price": 1725,
                        "currency": "USD",
                        "difference": "+15%"
                    }
                ),
                Notification(
                    type=NotificationType.PACKAGE_OFFER,
                    message="Nuevo paquete disponible para tours en Cancún",
                    item_id="package_456",
                    severity=NotificationSeverity.MEDIUM,
                    timestamp=datetime.now(),
                    data={
                        "items": ["Tour a Chichen Itzá", "Tour a Xcaret"],
                        "discount": "15%",
                        "valid_until": "2025-03-21"
                    }
                ),
                Notification(
                    type=NotificationType.SEASON_ALERT,
                    message="Se acerca temporada alta en Cancún",
                    item_id="season_789",
                    severity=NotificationSeverity.LOW,
                    timestamp=datetime.now(),
                    data={
                        "start_date": "2025-06-01",
                        "end_date": "2025-08-31",
                        "price_impact": "+25%"
                    }
                )
            ]
            
            for notification in notifications:
                st.session_state.notification_manager.add_notification(notification)
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
