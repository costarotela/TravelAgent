"""Aplicación principal de la agencia de viajes."""

import streamlit as st
from src.ui.pages.search import render_search_page
from src.ui.pages.budgets import render_budgets_page
from src.ui.pages.monitoring import render_monitoring_page


def initialize_session_state():
    """Inicializar estado de la sesión."""
    if "initialized" not in st.session_state:
        st.session_state.update(
            {
                "initialized": True,
                "current_page": "Búsqueda de Vuelos",
                "selected_budget_id": None,
                "search_results": None,
                "last_search": None,
                "redirect_to": None,
            }
        )


def handle_navigation():
    """Manejar la navegación entre páginas."""
    # Si hay una redirección pendiente, ejecutarla
    if st.session_state.redirect_to:
        st.session_state.current_page = st.session_state.redirect_to
        st.session_state.redirect_to = None
        st.rerun()

    # Menú de navegación
    with st.sidebar:
        st.title("Agencia de Viajes")
        pages = ["Búsqueda de Vuelos", "Presupuestos", "Monitoreo"]

        for page in pages:
            if st.button(
                page,
                key=f"nav_{page}",
                type=(
                    "primary" if st.session_state.current_page == page else "secondary"
                ),
            ):
                # Solo cambiar si es una página diferente
                if st.session_state.current_page != page:
                    st.session_state.current_page = page
                    # Limpiar estado si volvemos a búsqueda
                    if page == "Búsqueda de Vuelos":
                        st.session_state.search_results = None
                        st.session_state.last_search = None
                    st.rerun()


def main():
    """Función principal de la aplicación."""
    # Inicializar estado
    initialize_session_state()

    # Manejar navegación
    handle_navigation()

    # Renderizar página actual
    if st.session_state.current_page == "Búsqueda de Vuelos":
        render_search_page()
    elif st.session_state.current_page == "Presupuestos":
        render_budgets_page()
    else:
        render_monitoring_page()


if __name__ == "__main__":
    main()
