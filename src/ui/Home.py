"""Home page for Travel Agent."""
import streamlit as st
from src.auth import auth_manager, UserRole

st.set_page_config(
    page_title="Travel Agent",
    page_icon="✈️",
    layout="wide"
)

def show_login():
    """Show the login form."""
    st.title("Welcome to Travel Agent ✈️")
    st.write("Your personal travel planning assistant")
    
    # Two columns: Login and Features
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Login")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            remember = st.checkbox("Remember me")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("Please fill in all fields")
                else:
                    user = auth_manager.authenticate_user(username, password)
                    if user:
                        auth_manager.create_session(user)
                        st.success("Login successful! Redirecting...")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                        st.info("Default admin credentials: admin/admin123")
    
    with col2:
        st.subheader("Features")
        st.write("✓ Search and compare travel packages")
        st.write("✓ Real-time pricing and availability")
        st.write("✓ Personalized travel recommendations")
        st.write("✓ Secure booking and payment")
        st.write("✓ 24/7 customer support")
        st.write("✓ Manage your bookings online")

def show_home():
    """Show the home page."""
    # User profile in sidebar
    with st.sidebar:
        st.image("https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y", width=100)
        st.write(f"👋 Welcome, **{st.session_state.user['full_name'] or st.session_state.user['username']}**!")
        st.write(f"🔑 Role: {st.session_state.user['role']}")
        st.write("🔵 Online")
        
        st.markdown("---")
        
        # Logout at the bottom of sidebar
        if st.button("🚪 Logout", use_container_width=True):
            auth_manager.end_session()
            st.rerun()
    
    # Main content
    st.title("Travel Agent Dashboard")
    
    # Quick stats
    st.subheader("Quick Overview")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Active Bookings", "5", "2")
    with col2:
        st.metric("Total Budget", "$10,000", "$2,000")
    with col3:
        st.metric("Destinations", "12", "3")
    
    # Recent activity
    st.subheader("Recent Activity")
    activities = [
        {"date": "2025-02-15", "action": "New Booking", "details": "Paris, France - 7 days"},
        {"date": "2025-02-14", "action": "Payment Received", "details": "$2,500 - Booking #1234"},
        {"date": "2025-02-13", "action": "Itinerary Updated", "details": "Added museum tour to Tokyo trip"}
    ]
    
    for activity in activities:
        col1, col2, col3 = st.columns([1,2,3])
        with col1:
            st.write(activity["date"])
        with col2:
            st.write(f"**{activity['action']}**")
        with col3:
            st.write(activity["details"])
        st.markdown("---")

def main():
    """Main function."""
    # Clear session on startup
    if 'initialized' not in st.session_state:
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.initialized = True
    
    # If user is not logged in, show login page
    if "user" not in st.session_state:
        show_login()
        return
    
    # Verify token is still valid
    if not auth_manager.get_current_user():
        auth_manager.end_session()
        show_login()
        return
    
    # Show home page for logged-in users
    show_home()

if __name__ == "__main__":
    main()
