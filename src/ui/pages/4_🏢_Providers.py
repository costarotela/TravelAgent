"""Providers page."""
import streamlit as st

st.set_page_config(page_title="Providers - Travel Agent", layout="wide")

def show():
    """Show the providers page."""
    st.title("Provider Management")
    
    # Add New Provider Form
    st.subheader("Add New Provider")
    with st.form("add_provider_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Provider Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            
        with col2:
            country = st.selectbox("Country", ["USA", "UK", "France", "Spain", "Italy"])
            service_type = st.selectbox("Service Type", ["Hotel", "Flight", "Tour", "Transport"])
            status = st.selectbox("Status", ["Active", "Inactive", "Pending"])
            
        submit = st.form_submit_button("Add Provider")
        
        if submit:
            st.success(f"Provider {name} added successfully!")
    
    # Current Providers
    st.subheader("Current Providers")
    providers = [
        {
            "name": "Skylight Airways",
            "type": "Flight",
            "rating": "4.5/5",
            "status": "Active"
        },
        {
            "name": "LuxStay Hotels",
            "type": "Hotel",
            "rating": "4.8/5",
            "status": "Active"
        },
        {
            "name": "City Tours Inc.",
            "type": "Tour",
            "rating": "4.3/5",
            "status": "Active"
        }
    ]
    
    for provider in providers:
        col1, col2, col3, col4, col5 = st.columns([2,1,1,1,1])
        
        with col1:
            st.write(provider["name"])
        with col2:
            st.write(provider["type"])
        with col3:
            st.write(f"⭐ {provider['rating']}")
        with col4:
            st.write(provider["status"])
        with col5:
            st.button("Edit", key=f"edit_{provider['name']}")
        
        st.markdown("---")

if __name__ == "__main__":
    show()
