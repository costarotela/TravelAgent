"""
Dashboard de SmartTravelAgent implementado con Streamlit.

Este módulo implementa un dashboard interactivo para:
1. Visualización y gestión de presupuestos
2. Monitoreo de cambios en tiempo real
3. Aplicación de estrategias de reconstrucción
4. Seguimiento de métricas

Características principales:
- Actualización automática de datos
- Interfaz interactiva
- Visualización de métricas
- Gestión de presupuestos
- Control de reconstrucción

Uso:
    Para ejecutar el dashboard:
    ```bash
    streamlit run dashboard.py
    ```

Dependencias principales:
    - streamlit>=1.29.0
    - pandas
"""

import streamlit as st
from datetime import datetime
import pandas as pd
import logging
from typing import Dict, Any, List, Optional

from smart_travel_agency.core.budget.reconstruction import (
    BudgetReconstructionManager,
    ReconstructionStrategy
)
from smart_travel_agency.core.budget.validator import get_budget_validator
from smart_travel_agency.core.vendors.preferences import get_preference_manager
from smart_travel_agency.core.workflow import get_approval_workflow

class DashboardManager:
    """
    Gestor del Dashboard implementado con Streamlit.
    
    Esta clase maneja:
    1. Estado del dashboard
    2. Lógica de negocio
    3. Interacción con componentes core
    4. Actualización de datos
    5. Gestión de eventos
    """

    def __init__(self):
        """Inicializar el gestor del dashboard."""
        self.logger = logging.getLogger(__name__)
        
        # Componentes core
        self.reconstruction_manager = BudgetReconstructionManager()
        self.approval_workflow = get_approval_workflow()
        self.validator = get_budget_validator()
        self.preference_manager = get_preference_manager()
        
        # Configuración
        self.config = {
            "update_interval": 5,  # segundos
            "max_items": 10,
            "metrics_window": 3600,  # 1 hora
        }
        
        # Inicializar estado de Streamlit si no existe
        if 'active_budgets' not in st.session_state:
            st.session_state.active_budgets = []
        if 'metrics' not in st.session_state:
            st.session_state.metrics = {}
        if 'notifications' not in st.session_state:
            st.session_state.notifications = []

    def render(self):
        """Renderizar el dashboard completo."""
        st.set_page_config(
            page_title="SmartTravelAgent Dashboard",
            page_icon="✈️",
            layout="wide"
        )

        # Barra lateral con menú
        menu = st.sidebar.radio(
            "SmartTravelAgent",
            ["Presupuestos", "Reconstrucción", "Métricas"]
        )

        # Renderizar sección seleccionada
        if menu == "Presupuestos":
            self.render_budgets_section()
        elif menu == "Reconstrucción":
            self.render_reconstruction_section()
        elif menu == "Métricas":
            self.render_metrics_section()

    def render_budgets_section(self):
        """Renderizar sección de presupuestos."""
        st.title("Gestión de Presupuestos")
        
        # Métricas principales
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Presupuestos Activos",
                len(st.session_state.active_budgets)
            )
        with col2:
            st.metric(
                "Pendientes",
                sum(1 for b in st.session_state.active_budgets if b['status'] == 'pending')
            )
        with col3:
            st.metric(
                "Aprobados Hoy",
                sum(1 for b in st.session_state.active_budgets 
                    if b['status'] == 'approved' and 
                    b['updated_at'].date() == datetime.now().date())
            )

        # Lista de presupuestos
        st.subheader("Presupuestos Activos")
        for budget in st.session_state.active_budgets:
            with st.expander(f"{budget['title']} - {budget['status']}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**ID:** {budget['id']}")
                    st.write(f"**Cliente:** {budget['client']}")
                    st.write(f"**Última actualización:** {budget['updated_at']}")
                with col2:
                    st.button("Ver Detalles", key=f"view_{budget['id']}")
                    if budget['status'] == 'draft':
                        st.button("Editar", key=f"edit_{budget['id']}")

    def render_reconstruction_section(self):
        """Renderizar sección de reconstrucción de presupuestos."""
        st.title("Reconstrucción de Presupuestos")

        # Selector de estrategia
        strategy = st.selectbox(
            "Estrategia de Reconstrucción",
            [
                "PRESERVE_MARGIN - Mantener Margen",
                "PRESERVE_PRICE - Mantener Precio",
                "ADJUST_PROPORTIONALLY - Ajuste Proporcional",
                "BEST_ALTERNATIVE - Mejor Alternativa"
            ]
        )

        # Configuración de reconstrucción
        with st.expander("Configuración de Reconstrucción"):
            st.slider("Tolerancia de Cambio (%)", 0, 100, 10)
            st.checkbox("Notificar Cambios Significativos")
            st.checkbox("Auto-aplicar Estrategia")

        # Estado de reconstrucción
        if 'reconstruction_status' in st.session_state:
            status = st.session_state.reconstruction_status
            st.info(f"Estado: {status['message']}")

        # Botón de aplicar
        if st.button("Aplicar Estrategia"):
            self._apply_reconstruction_strategy(strategy.split(" - ")[0])

    def render_metrics_section(self):
        """Renderizar sección de métricas."""
        st.title("Métricas y KPIs")

        # Período de tiempo
        period = st.selectbox(
            "Período",
            ["Última Hora", "Último Día", "Última Semana", "Último Mes"]
        )

        # Métricas en tiempo real
        if 'metrics' in st.session_state:
            metrics = st.session_state.metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Tasa de Aprobación",
                    f"{metrics.get('approval_rate', 0)}%",
                    f"{metrics.get('approval_rate_change', 0)}%"
                )
            with col2:
                st.metric(
                    "Tiempo Promedio de Proceso",
                    f"{metrics.get('avg_process_time', 0)} min",
                    f"{metrics.get('process_time_change', 0)} min"
                )
            with col3:
                st.metric(
                    "Reconstrucciones Exitosas",
                    metrics.get('successful_reconstructions', 0),
                    metrics.get('reconstruction_change', 0)
                )

    def _apply_reconstruction_strategy(self, strategy: str):
        """
        Aplicar estrategia de reconstrucción.
        
        Args:
            strategy: Nombre de la estrategia a aplicar
        """
        try:
            result = self.reconstruction_manager.apply_strategy(
                strategy=ReconstructionStrategy[strategy]
            )
            st.session_state.reconstruction_status = {
                "success": True,
                "message": f"Estrategia {strategy} aplicada exitosamente"
            }
            self.logger.info(f"Estrategia {strategy} aplicada: {result}")
        except Exception as e:
            st.session_state.reconstruction_status = {
                "success": False,
                "message": f"Error al aplicar estrategia: {str(e)}"
            }
            self.logger.error(f"Error al aplicar estrategia {strategy}: {e}")

    def update_data(self):
        """Actualizar datos del dashboard."""
        # Actualizar presupuestos
        st.session_state.active_budgets = self._fetch_active_budgets()
        
        # Actualizar métricas
        st.session_state.metrics = self._calculate_metrics()
        
        # Actualizar cada 5 segundos
        st.experimental_rerun()

    def _fetch_active_budgets(self) -> List[Dict[str, Any]]:
        """
        Obtener presupuestos activos.
        
        Returns:
            Lista de presupuestos activos
        """
        # Implementar lógica de obtención de presupuestos
        return []

    def _calculate_metrics(self) -> Dict[str, Any]:
        """
        Calcular métricas del dashboard.
        
        Returns:
            Diccionario con métricas calculadas
        """
        # Implementar cálculo de métricas
        return {}

# Instancia global
dashboard = DashboardManager()

def run_dashboard():
    """Ejecutar el dashboard de Streamlit."""
    dashboard.render()
    
if __name__ == "__main__":
    run_dashboard()
