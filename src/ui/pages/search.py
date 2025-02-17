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
        
        monitor.log_metric("budget_created", 1, {"type": "flight"})
        return True
    except Exception as e:
        st.error(f"Error al crear presupuesto: {str(e)}")
        monitor.log_error(e, {"action": "create_budget"})
        return False

def filter_and_sort_results(results: List[TravelPackage], price_range, flight_type, sort_by, cabin_class=None):
    """Filtrar y ordenar resultados."""
    filtered = []
    
    for flight in results:
        # Filtrar por precio
        if not (price_range[0] <= flight.price <= price_range[1]):
            continue
            
        # Filtrar por tipo de vuelo
        if flight_type != "Todos" and flight.details.get("type") != flight_type.lower():
            continue
            
        # Filtrar por clase de cabina
        if cabin_class and cabin_class != "Todas" and flight.details.get("cabin_class") != cabin_class:
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

def show_flight_details(flight: TravelPackage, adults: int):
    """Mostrar detalles del vuelo en un formato mejorado."""
    with st.container():
        # Usar columnas para mejor organización
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            st.subheader(f"{flight.origin} → {flight.destination}")
            st.caption(f"Fecha: {flight.departure_date.strftime('%Y-%m-%d')}")
            st.write(f"🛫 **Aerolínea:** {flight.details.get('airline', 'N/A')}")
            st.write(f"✈️ **Vuelo:** {flight.details.get('flight_number', 'N/A')}")
        
        with col2:
            st.write(f"⏱️ **Duración:** {flight.details.get('duration', 'N/A')}")
            st.write(f"🎫 **Clase:** {flight.details.get('cabin_class', 'N/A')}")
            st.write(f"🧳 **Equipaje:** {flight.details.get('baggage', 'N/A')}")
            if flight.details.get("stops"):
                st.write(f"🛑 **Escalas:** {', '.join(flight.details['stops'])}")
        
        with col3:
            st.write(f"💰 **Precio:**")
            st.markdown(f"<h3 style='text-align: center;'>${flight.price:.0f}</h3>", unsafe_allow_html=True)
            st.caption(flight.currency)
            
            if st.button("📄 Crear Presupuesto", key=f"btn_{flight.id}"):
                with st.spinner("Creando presupuesto..."):
                    if create_budget_from_flight(flight, adults):
                        st.success("¡Presupuesto creado!")
        
        st.divider()

def export_results_to_excel(results: List[TravelPackage]):
    """Exportar resultados a Excel."""
    try:
        # Convertir resultados a DataFrame
        data = []
        for flight in results:
            data.append({
                "Origen": flight.origin,
                "Destino": flight.destination,
                "Fecha": flight.departure_date,
                "Aerolínea": flight.details.get("airline"),
                "Vuelo": flight.details.get("flight_number"),
                "Clase": flight.details.get("cabin_class"),
                "Duración": flight.details.get("duration"),
                "Equipaje": flight.details.get("baggage"),
                "Precio": flight.price,
                "Moneda": flight.currency
            })
        
        df = pd.DataFrame(data)
        
        # Guardar a Excel
        excel_file = "resultados_busqueda.xlsx"
        df.to_excel(excel_file, index=False)
        
        # Leer el archivo para devolverlo
        with open(excel_file, "rb") as f:
            return f.read()
    except Exception as e:
        st.error(f"Error al exportar resultados: {str(e)}")
        monitor.log_error(e, {"action": "export_results"})
        return None

def render_search_page():
    """Renderizar página de búsqueda."""
    st.title("Búsqueda de Vuelos")
    
    # Inicializar estado
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
        submitted = st.form_submit_button("🔍 Buscar Vuelos")
        
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
                try:
                    provider = AeroProvider({"name": "aero"})
                    criteria = SearchCriteria(**params)
                    results = asyncio.run(provider.search_packages(criteria))
                    
                    if not results:
                        st.warning("No se encontraron vuelos.")
                        monitor.log_metric("search_empty", 1)
                    else:
                        st.session_state.search_results = results
                        monitor.log_metric("search_success", 1, {"results": len(results)})
                except Exception as e:
                    st.error(f"Error al buscar vuelos: {str(e)}")
                    monitor.log_error(e, {"action": "search"})
    
    # Mostrar resultados si existen
    if st.session_state.search_results:
        st.subheader("Vuelos Encontrados")
        
        # Filtros y ordenamiento en columnas
        col1, col2, col3, col4 = st.columns(4)
        
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
            # Clase de cabina
            cabin_class = st.selectbox(
                "Clase",
                options=["Todas", "Economy", "Business", "First"]
            )
        
        with col4:
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
            sort_by,
            cabin_class
        )
        
        # Mostrar contador de resultados y botón de exportar
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"📊 {len(filtered_results)} vuelos encontrados")
        with col2:
            if filtered_results:
                excel_data = export_results_to_excel(filtered_results)
                if excel_data:
                    st.download_button(
                        "📥 Exportar a Excel",
                        excel_data,
                        "resultados_busqueda.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        
        if not filtered_results:
            st.warning("No hay vuelos que coincidan con los filtros seleccionados.")
        else:
            # Mostrar resultados filtrados
            for flight in filtered_results:
                show_flight_details(flight, adults)

if __name__ == "__main__":
    render_search_page()
