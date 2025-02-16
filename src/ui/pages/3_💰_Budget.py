"""Budget page."""
import streamlit as st
from datetime import datetime, timedelta

st.set_page_config(page_title="Budget - Travel Agent", layout="wide")

def show():
    """Show the budget page."""
    st.title("Budget Management")
    
    # Budget Overview
    st.subheader("Budget Overview")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Budget", "$50,000", delta="$10,000")
    with col2:
        st.metric("Spent", "$30,000", delta="-$5,000")
    with col3:
        st.metric("Remaining", "$20,000", delta="$5,000")
    
    # Budget Allocation
    st.subheader("Budget Allocation")
    data = {
        'Category': ['Flights', 'Hotels', 'Activities', 'Transport', 'Other'],
        'Amount': [15000, 20000, 8000, 5000, 2000]
    }
    st.bar_chart(data, x='Category')
    
    # Recent Transactions
    st.subheader("Recent Transactions")
    transactions = [
        {"date": "2025-02-15", "description": "Flight Booking - Paris", "amount": "-$1,200"},
        {"date": "2025-02-14", "description": "Hotel Reservation - London", "amount": "-$800"},
        {"date": "2025-02-13", "description": "Budget Increase", "amount": "+$5,000"},
    ]
    
    for tx in transactions:
        col1, col2, col3 = st.columns([1,2,1])
        with col1:
            st.write(tx["date"])
        with col2:
            st.write(tx["description"])
        with col3:
            st.write(tx["amount"])
        st.markdown("---")

if __name__ == "__main__":
    show()
