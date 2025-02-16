"""Search page."""
import streamlit as st
from datetime import datetime, timedelta

st.set_page_config(page_title="Search - Travel Agent", layout="wide")

def show():
    """Show the search page."""
    st.title("Search Destinations")
    
    # Search form
    with st.form("search_form"):
        destination = st.text_input("Where do you want to go?")
        col1, col2 = st.columns(2)
        
        with col1:
            departure = st.date_input("Departure Date")
        
        with col2:
            duration = st.number_input("Duration (days)", min_value=1, max_value=30, value=7)
        
        travelers = st.number_input("Number of Travelers", min_value=1, max_value=10, value=2)
        
        submitted = st.form_submit_button("Search")
        
        if submitted:
            st.success("Searching for your perfect trip...")
            
            # Example results
            st.subheader("Search Results")
            
            for i in range(3):
                with st.container():
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"### Package {i+1}")
                        st.write(f"✈️ Flight + 🏨 Hotel in {destination or 'Paris'}")
                        st.write(f"🗓️ {duration} days, {travelers} travelers")
                        st.write("⭐⭐⭐⭐ (125 reviews)")
                    
                    with col2:
                        st.markdown("### $1,299")
                        st.markdown("per person")
                        st.button("Book Now", key=f"book_{i}")
                    
                    st.markdown("---")

if __name__ == "__main__":
    show()
