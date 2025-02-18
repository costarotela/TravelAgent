"""Aplicación principal de Costa Rotela Travel."""

import streamlit as st
from typing import Dict, Any

from src.ui.pages import home, search, budgets
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
        st.session_state["page"] = "Inicio"
    if "redirect_to" not in st.session_state:
        st.session_state["redirect_to"] = None
    if "error" not in st.session_state:
        st.session_state["error"] = None


def handle_navigation():
    """Manejar navegación entre páginas."""
    # Procesar redirección si existe
    if st.session_state.get("redirect_to"):
        st.session_state["page"] = st.session_state["redirect_to"]
        st.session_state["redirect_to"] = None
        st.rerun()
        return  # Salir después de la redirección

    try:
        # Menú de navegación
        with st.sidebar:
            st.image("assets/logo.png", width=200)
            st.title("Costa Rotela Travel")

            # Enlaces de navegación
            pages = {
                "🏠 Inicio": "Inicio",
                "🔍 Búsqueda": "Búsqueda",
                "📄 Presupuestos": "Presupuestos",
            }

            for label, page in pages.items():
                if st.sidebar.button(
                    label,
                    use_container_width=True,
                    type="primary" if st.session_state["page"] == page else "secondary",
                ):
                    st.session_state["page"] = page
                    st.rerun()

            # Información adicional
            with st.sidebar.expander("ℹ️ Ayuda"):
                st.write(
                    """
                ### Guía Rápida
                
                1. **Inicio**: Dashboard y búsqueda rápida
                2. **Búsqueda**: Buscar y comparar vuelos
                3. **Presupuestos**: Gestionar presupuestos
                
                Para soporte, contacte a:
                support@costarotela.com
                """
                )
    except Exception as e:
        # Si hay error en el sidebar (por ejemplo, en tests), ignorarlo
        pass


def render_error(error: AppError):
    """Renderizar error en la interfaz."""
    st.error(error.message)

    with st.expander("Detalles del error"):
        if error.details:
            st.json(error.details)
        if error.traceback:
            st.code(error.traceback)

    if st.button("🏠 Volver al Inicio"):
        st.session_state["page"] = "Inicio"
        st.session_state["error"] = None
        st.rerun()


def main():
    """Función principal de la aplicación."""
    try:
        # Inicializar estado
        initialize_session_state()

        # Si hay un error, mostrarlo
        if st.session_state.get("error"):
            render_error(st.session_state["error"])
            return

        # Manejar navegación
        handle_navigation()

        # Renderizar página actual
        if st.session_state["page"] == "Inicio":
            home.render_home_page()
        elif st.session_state["page"] == "Búsqueda":
            search.render_search_page()
        elif st.session_state["page"] == "Presupuestos":
            budgets.render_budgets_page()

        # Registrar vista de página
        monitor.log_metric("page_view", 1, {"page": st.session_state["page"]})

    except Exception as e:
        # Manejar error y guardarlo en el estado
        context = {"page": st.session_state.get("page", "unknown")}
        app_error = handle_error(e, context)
        st.session_state["error"] = app_error
        st.rerun()


if __name__ == "__main__":
    main()
