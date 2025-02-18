"""Authentication manager for the application."""

from typing import Optional, Dict

from src.auth.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
)
from src.auth.models import UserRole


class AuthManager:
    """Authentication manager class."""

    def __init__(self):
        """Initialize the auth manager."""
        self.users_db = {
            "admin": {
                "username": "admin",
                "full_name": "Administrator",
                "email": "admin@example.com",
                "hashed_password": get_password_hash("admin123"),
                "role": UserRole.ADMIN,
            }
        }

    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate a user and return user data if successful."""
        user = self.users_db.get(username)
        if user and verify_password(password, user["hashed_password"]):
            # Create a copy without the hashed password
            user_data = user.copy()
            del user_data["hashed_password"]
            return user_data
        return None

    def create_session(self, user: Dict) -> None:
        """Create a new session for the user."""
        import streamlit as st

        # Create access token
        token = create_access_token({"sub": user["username"]})
        # Store in session state
        st.session_state.token = token
        st.session_state.user = user

    def get_current_user(self) -> Optional[Dict]:
        """Get the current logged-in user."""
        import streamlit as st

        if "token" not in st.session_state:
            return None

        # Decode and verify token
        token_data = decode_token(st.session_state.token)
        if not token_data:
            return None

        # Get username from token
        username = token_data.get("sub")
        if not username:
            return None

        # Get user data
        user = self.users_db.get(username)
        if not user:
            return None

        # Return user data without password
        user_data = user.copy()
        del user_data["hashed_password"]
        return user_data

    def end_session(self) -> None:
        """End the current session."""
        import streamlit as st

        if "token" in st.session_state:
            del st.session_state.token
        if "user" in st.session_state:
            del st.session_state.user

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str = "",
        role: UserRole = UserRole.CLIENT,
    ) -> Optional[Dict]:
        """Register a new user."""
        if username in self.users_db:
            return None

        user = {
            "username": username,
            "full_name": full_name,
            "email": email,
            "hashed_password": get_password_hash(password),
            "role": role,
        }
        self.users_db[username] = user

        # Return user data without password
        user_data = user.copy()
        del user_data["hashed_password"]
        return user_data


# Create a singleton instance
auth_manager = AuthManager()
