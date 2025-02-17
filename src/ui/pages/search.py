"""Página de búsqueda simple."""
import streamlit as st
from datetime import datetime, timedelta
import asyncio
from typing import List

from src.core.providers import AeroProvider, SearchCriteria, TravelPackage
from src.core.budget import create_budget_from_package
from src.core.budget.storage import BudgetStorage
from src.utils.database import Database

def save_search_params(params):
    """Guardar parámetros de búsqueda en el estado."""
    st.session_state.last_search = params

def create_budget_from_flight(flight, adults):
    """Crear y guardar un nuevo presupuesto."""
    try:
        # Crear presupuesto
        budget = create_budget_from_package(
            package=flight,
            customer_name="",
            passengers={"adults": adults},
            valid_days=3
        )
        
        # Guardar en base de datos
        storage = BudgetStorage(Database())
        budget_id = storage.save_budget(budget)
        
        # Actualizar estado para redirección
        st.session_state.selected_budget_id = budget_id
        st.session_state.redirect_to = "Presupuestos"
        
        return True
    except Exception as e:
        st.error(f"Error al crear presupuesto: {str(e)}")
        return False

def filter_and_sort_results(results: List[TravelPackage], price_range, flight_type, sort_by):
    """Filtrar y ordenar resultados."""
    filtered = []
    
    for flight in results:
        # Filtrar por precio
        if not (price_range[0] <= flight.price <= price_range[1]):
            continue
            
        # Filtrar por tipo de vuelo
        if flight_type != "Todos" and flight.details.get("type") != flight_type.lower():
            continue
            
        filtered.append(flight)
    
    # Ordenar resultados
    if sort_by == "Precio (menor a mayor)":
        filtered.sort(key=lambda x: x.price)
    elif sort_by == "Precio (mayor a menor)":
        filtered.sort(key=lambda x: x.price, reverse=True)
    elif sort_by == "Duración":
        filtered.sort(key=lambda x: x.details.get("duration", ""))
    
    return filtered

def render_search_page():
    """Renderizar página de búsqueda."""
    st.title("Búsqueda de Vuelos")
    
    # Inicializar estado de resultados si no existe
    if "search_results" not in st.session_state:
        st.session_state.search_results = []
        
    if "last_search" not in st.session_state:
        st.session_state.last_search = None
    
    # Formulario de búsqueda
    with st.form(key="search_form"):
        # Campos de búsqueda
        col1, col2 = st.columns(2)
        
        with col1:
            origin = st.text_input(
                "Origen",
                value=st.session_state.last_search["origin"] if st.session_state.last_search else "Buenos Aires"
            )
            
            departure_date = st.date_input(
                "Fecha de Salida",
                value=st.session_state.last_search["departure_date"] if st.session_state.last_search else datetime.now().date() + timedelta(days=1),
                min_value=datetime.now().date()
            )
        
        with col2:
            destination = st.text_input(
                "Destino",
                value=st.session_state.last_search["destination"] if st.session_state.last_search else "Madrid"
            )
            
            adults = st.number_input(
                "Adultos",
                min_value=1,
                value=st.session_state.last_search["adults"] if st.session_state.last_search else 1
            )
        
        # Botón de búsqueda
        submitted = st.form_submit_button("Buscar Vuelos")
        
        if submitted:
            # Guardar parámetros
            params = {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
                "adults": adults
            }
            save_search_params(params)
            
            # Realizar búsqueda
            with st.spinner("Buscando vuelos..."):
                provider = AeroProvider({"name": "aero"})
                criteria = SearchCriteria(**params)
                results = asyncio.run(provider.search_packages(criteria))
                
                if not results:
                    st.warning("No se encontraron vuelos.")
                else:
                    st.session_state.search_results = results
    
    # Mostrar resultados si existen
    if st.session_state.search_results:
        st.subheader("Vuelos Encontrados")
        
        # Filtros y ordenamiento
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Rango de precios
            min_price = min(flight.price for flight in st.session_state.search_results)
            max_price = max(flight.price for flight in st.session_state.search_results)
            price_range = st.slider(
                "Rango de Precios (USD)",
                min_value=float(min_price),
                max_value=float(max_price),
                value=(float(min_price), float(max_price)),
                step=50.0
            )
        
        with col2:
            # Tipo de vuelo
            flight_type = st.selectbox(
                "Tipo de Vuelo",
                options=["Todos", "Direct", "Stopover", "Premium"]
            )
        
        with col3:
            # Ordenamiento
            sort_by = st.selectbox(
                "Ordenar por",
                options=["Precio (menor a mayor)", "Precio (mayor a menor)", "Duración"]
            )
        
        # Filtrar y ordenar resultados
        filtered_results = filter_and_sort_results(
            st.session_state.search_results,
            price_range,
            flight_type,
            sort_by
        )
        
        if not filtered_results:
            st.warning("No hay vuelos que coincidan con los filtros seleccionados.")
        else:
            # Mostrar resultados filtrados
            for flight in filtered_results:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**{flight.origin} → {flight.destination}**")
                        st.write(f"Fecha: {flight.departure_date.strftime('%Y-%m-%d')}")
                        st.write(f"Tipo: {flight.details.get('type', 'N/A').title()}")
                        st.write(f"Aerolínea: {flight.details.get('airline', 'N/A')}")
                        st.write(f"Clase: {flight.details.get('cabin_class', 'N/A')}")
                        st.write(f"Duración: {flight.details.get('duration', 'N/A')}")
                        if flight.details.get("stops"):
                            st.write(f"Escalas: {', '.join(flight.details['stops'])}")
                    
                    with col2:
                        st.write(f"Precio: ${flight.price:.0f} {flight.currency}")
                        if st.button("Crear Presupuesto", key=f"btn_{flight.id}"):
                            create_budget_from_flight(flight, adults)
                    
                    st.divider()

if __name__ == "__main__":
    render_search_page()
