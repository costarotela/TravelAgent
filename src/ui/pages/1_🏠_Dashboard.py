"""Dashboard page."""
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from src.auth import auth_manager

# Verify user is logged in
if "user" not in st.session_state or not auth_manager.get_current_user():
    st.error("Please log in to access this page")
    st.stop()

# Page content
st.set_page_config(page_title="Dashboard - Travel Agent", layout="wide")
st.title("Dashboard")

# Create columns for metrics
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Active Bookings", value="5")

with col2:
    st.metric(label="Total Budget", value="$10,000", delta="$2,000")

with col3:
    st.metric(label="Destinations", value="12", delta="2")

# Add a chart
st.subheader("Monthly Bookings")
data = {
    'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
    'Bookings': [4, 6, 3, 8, 5]
}
st.line_chart(data)

if __name__ == "__main__":
    pass
