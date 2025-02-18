"""Página de búsqueda simple."""

import streamlit as st
from datetime import datetime, timedelta
import asyncio
from typing import List
import pandas as pd

from src.core.providers import AeroProvider, SearchCriteria, TravelPackage
from src.core.budget import create_budget_from_package
from src.core.budget.storage import BudgetStorage
from src.utils.database import Database
from src.utils.monitoring import monitor


def create_budget_from_flight(flight: TravelPackage, adults: int) -> bool:
    """Crear y guardar un nuevo presupuesto."""
    try:
        # Crear presupuesto
        budget = create_budget_from_package(
            package=flight,
            customer_name="Cliente Nuevo",  # Valor por defecto
            passengers={"adults": adults},
            valid_days=3,
        )

        # Guardar en base de datos
        storage = BudgetStorage(Database())
        budget_id = storage.save_budget(budget)

        # Actualizar estado para redirección
        if not hasattr(st.session_state, "selected_budget_id"):
            setattr(st.session_state, "selected_budget_id", None)
        if not hasattr(st.session_state, "redirect_to"):
            setattr(st.session_state, "redirect_to", None)

        st.session_state.selected_budget_id = budget_id
        st.session_state.redirect_to = "Presupuestos"

        # Registrar métrica
        monitor.log_metric("budget_created", 1, {"type": "flight"})
        return True

    except Exception as e:
        st.error(f"Error al crear presupuesto: {str(e)}")
        monitor.log_error(e, {"action": "create_budget"})
        return False


def filter_results(
    results: List[TravelPackage], max_price: float = None
) -> List[TravelPackage]:
    """Filtrar resultados por precio máximo."""
    if not max_price:
        return results
    return [r for r in results if r.price <= max_price]


def show_flight_details(flight: TravelPackage, adults: int):
    """Mostrar detalles del vuelo en formato simple."""
    with st.container():
        col1, col2 = st.columns([3, 1])

        with col1:
            st.subheader(f"{flight.origin} → {flight.destination}")
            st.write(f"🛫 {flight.departure_date.strftime('%d/%m/%Y %H:%M')}")

            details = [
                f"✈️ {flight.details.get('airline', 'N/A')}",
                f"🎫 {flight.details.get('cabin_class', 'N/A')}",
                f"🧳 {flight.details.get('baggage', 'N/A')}",
            ]
            st.write(" | ".join(details))

        with col2:
            st.write("💰 **Precio total:**")
            total = flight.price * adults
            st.markdown(
                f"<h3 style='text-align: center;'>${total:.0f}</h3>",
                unsafe_allow_html=True,
            )
            st.caption(f"${flight.price:.0f} por persona")

            if st.button(
                "📄 Crear Presupuesto", key=f"btn_{flight.id}", type="primary"
            ):
                with st.spinner("Creando presupuesto..."):
                    if create_budget_from_flight(flight, adults):
                        st.success("¡Presupuesto creado!")

        st.divider()


def render_search_page():
    """Renderizar página de búsqueda simplificada."""
    st.title("Búsqueda de Vuelos")

    # Inicializar resultados
    if "search_results" not in st.session_state:
        st.session_state.search_results = []

    # Formulario de búsqueda simple
    with st.form(key="search_form"):
        col1, col2 = st.columns(2)

        with col1:
            origin = st.text_input("Origen", value="Buenos Aires")
            departure_date = st.date_input(
                "Fecha de Salida",
                value=datetime.now().date() + timedelta(days=1),
                min_value=datetime.now().date(),
            )

        with col2:
            destination = st.text_input("Destino", value="Madrid")
            adults = st.number_input("Pasajeros", min_value=1, value=1)

        submitted = st.form_submit_button("🔍 Buscar Vuelos", use_container_width=True)

    # Realizar búsqueda
    if submitted:
        with st.spinner("Buscando vuelos..."):
            try:
                # Crear proveedor y criterios
                provider = AeroProvider({"name": "aero"})
                criteria = SearchCriteria(
                    origin=origin,
                    destination=destination,
                    departure_date=datetime.combine(
                        departure_date, datetime.min.time()
                    ),
                    adults=adults,
                )

                # Buscar vuelos
                results = asyncio.run(provider.search_packages(criteria))

                if not results:
                    st.warning(
                        "No se encontraron vuelos para los criterios seleccionados."
                    )
                    monitor.log_metric("search_empty", 1)
                else:
                    st.session_state.search_results = results
                    monitor.log_metric("search_success", 1, {"results": len(results)})

            except Exception as e:
                st.error(f"Error al buscar vuelos: {str(e)}")
                monitor.log_error(e, {"action": "search"})

    # Mostrar resultados
    if st.session_state.search_results:
        st.subheader(f"Vuelos Encontrados ({len(st.session_state.search_results)})")

        # Filtro simple por precio máximo
        max_price = st.slider(
            "Precio máximo por persona (USD)",
            min_value=float(min(r.price for r in st.session_state.search_results)),
            max_value=float(max(r.price for r in st.session_state.search_results)),
            value=float(max(r.price for r in st.session_state.search_results)),
            step=50.0,
        )

        # Filtrar y mostrar resultados
        filtered_results = filter_results(st.session_state.search_results, max_price)

        if not filtered_results:
            st.info("No hay vuelos disponibles para el precio máximo seleccionado.")
        else:
            # Mostrar resultados en orden de precio
            for flight in sorted(filtered_results, key=lambda x: x.price):
                show_flight_details(flight, adults)


if __name__ == "__main__":
    render_search_page()
