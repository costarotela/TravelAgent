"""Aplicación principal de Costa Rotela Travel."""

import streamlit as st
from typing import Dict, Any

from src.ui.pages import render_home_page, render_search_page, render_budget_page
from src.utils.monitoring import monitor
from src.utils.error_handling import handle_error, AppError


# Configuración de la página
st.set_page_config(
    page_title="Costa Rotela Travel",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def initialize_session_state():
    """Inicializar estado de la sesión."""
    if "page" not in st.session_state:
        st.session_state.page = "🏠 Inicio"
    if "error" not in st.session_state:
        st.session_state.error = None


def handle_navigation():
    """Manejar navegación entre páginas."""
    try:
        # Menú principal
        pages = {
            "🏠 Inicio": render_home_page,
            "🔍 Búsqueda": render_search_page,
            "💰 Presupuestos": render_budget_page,
        }

        # Selección de página
        st.sidebar.title("Costa Rotela Travel")
        st.sidebar.divider()

        selected_page = st.sidebar.selectbox(
            "Navegación", list(pages.keys()), key="page"
        )

        # Renderizar página seleccionada
        pages[selected_page]()

        # Limpiar error si existe
        if st.session_state.error:
            st.session_state.error = None

    except Exception as e:
        error = handle_error(e)
        st.session_state.error = error
        monitor.error(str(error))


def render_error(error: AppError):
    """Renderizar error en la interfaz."""
    st.error(
        f"""
        **Error: {error.title}**

        {error.message}

        Si el problema persiste, contacte al soporte técnico.
        """
    )


def main():
    """Función principal de la aplicación."""
    try:
        # Inicializar estado
        initialize_session_state()

        # Manejar navegación
        handle_navigation()

        # Mostrar error si existe
        if st.session_state.error:
            render_error(st.session_state.error)

    except Exception as e:
        error = handle_error(e)
        st.error(
            f"""
            **Error crítico**

            Ha ocurrido un error inesperado: {str(error)}

            Por favor, recargue la página o contacte al soporte técnico.
            """
        )
        monitor.error(str(error))


if __name__ == "__main__":
    main()
