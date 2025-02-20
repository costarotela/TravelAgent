"""Página de búsqueda de vuelos."""

import streamlit as st
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Any

from src.core.providers import AeroProvider, SearchCriteria, TravelPackage
from src.ui.client import TravelAgentClient
from src.utils.monitoring import monitor


async def create_budget_from_flight(flight: TravelPackage, adults: int) -> bool:
    """Crear y guardar un nuevo presupuesto."""
    try:
        async with TravelAgentClient() as client:
            # Crear sesión
            await client.create_session(
                vendor_id="default",  # TODO: Implementar autenticación
                customer_id="new_customer",  # TODO: Implementar gestión de clientes
            )

            # Agregar paquete
            await client.add_package(flight.to_dict())

            return True

    except Exception as e:
        monitor.error(f"Error al crear presupuesto: {str(e)}")
        return False


def filter_results(
    results: List[TravelPackage], max_price: float = None
) -> List[TravelPackage]:
    """Filtrar resultados por precio máximo."""
    if max_price is None:
        return results
    return [r for r in results if r.price <= max_price]


def show_flight_details(flight: TravelPackage, adults: int):
    """Mostrar detalles del vuelo en formato simple."""
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Detalles del vuelo:**")
        st.write(f"- Origen: {flight.origin}")
        st.write(f"- Destino: {flight.destination}")
        st.write(f"- Fecha ida: {flight.departure_date.strftime('%d/%m/%Y %H:%M')}")
        if flight.return_date:
            st.write(f"- Fecha vuelta: {flight.return_date.strftime('%d/%m/%Y %H:%M')}")
        st.write(f"- Aerolínea: {flight.details.get('airline', 'No disponible')}")
        st.write(
            f"- Número de vuelo: {flight.details.get('flight_number', 'No disponible')}"
        )

    with col2:
        st.write("**Precio y disponibilidad:**")
        st.write(f"- Precio por persona: {flight.price} {flight.currency}")
        st.write(
            f"- Total para {adults} personas: {flight.price * adults} {flight.currency}"
        )
        st.write(
            f"- Asientos disponibles: {flight.details.get('seats_available', 'No disponible')}"
        )
        st.write(f"- Clase: {flight.details.get('cabin_class', 'Economy')}")
        st.write(f"- Equipaje: {flight.details.get('baggage', '23kg')}")

    if st.button("Crear presupuesto"):
        if asyncio.run(create_budget_from_flight(flight, adults)):
            st.success("¡Presupuesto creado exitosamente!")
        else:
            st.error("Error al crear el presupuesto. Por favor intente nuevamente.")


def render_search_page():
    """Renderizar página de búsqueda simplificada."""
    st.title("🔍 Búsqueda de vuelos")

    # Formulario de búsqueda
    with st.form("search_form"):
        col1, col2 = st.columns(2)

        with col1:
            origin = st.text_input("Origen", "BUE")
            departure_date = st.date_input(
                "Fecha ida", datetime.now() + timedelta(days=7)
            )
            adults = st.number_input("Adultos", 1, 9, 1)

        with col2:
            destination = st.text_input("Destino", "MDZ")
            return_date = st.date_input(
                "Fecha vuelta", datetime.now() + timedelta(days=14)
            )
            max_price = st.number_input("Precio máximo", 0, 100000, 50000)

        submitted = st.form_submit_button("Buscar")

    if submitted:
        with st.spinner("Buscando vuelos..."):
            # Crear criterio de búsqueda
            criteria = SearchCriteria(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                adults=adults,
            )

            # Buscar vuelos
            provider = AeroProvider()
            results = asyncio.run(provider.search(criteria))

            # Filtrar por precio máximo
            filtered_results = filter_results(results, max_price)

            if not filtered_results:
                st.warning("No se encontraron vuelos que coincidan con tu búsqueda.")
                return

            # Mostrar resultados
            st.write(f"Se encontraron {len(filtered_results)} vuelos:")
            for flight in filtered_results:
                with st.expander(
                    f"{flight.origin} → {flight.destination} - "
                    f"{flight.price} {flight.currency}"
                ):
                    show_flight_details(flight, adults)


if __name__ == "__main__":
    render_search_page()
