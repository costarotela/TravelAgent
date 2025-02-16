"""User data storage management."""
import json
import os
from typing import Dict, Optional

from src.auth.models import User, UserRole

class UserStorage:
    """Manages user data persistence."""

    def __init__(self):
        """Initialize the storage."""
        self.storage_dir = os.path.join(os.path.dirname(__file__), "data")
        self.users_file = os.path.join(self.storage_dir, "users.json")
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        """Ensure storage directory and files exist."""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
        
        if not os.path.exists(self.users_file):
            self._save_users({})

    def _save_users(self, users: Dict[str, dict]):
        """Save users to file."""
        with open(self.users_file, "w") as f:
            json.dump(users, f, indent=2)

    def _load_users(self) -> Dict[str, dict]:
        """Load users from file."""
        if not os.path.exists(self.users_file):
            return {}
        
        with open(self.users_file, "r") as f:
            return json.load(f)

    def save_user(self, user: User):
        """Save a user to storage."""
        users = self._load_users()
        users[user.username] = {
            "username": user.username,
            "email": user.email,
            "hashed_password": user.hashed_password,
            "role": user.role,
            "full_name": user.full_name,
            "disabled": user.disabled,
            "created_at": user.created_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
        self._save_users(users)

    def get_user(self, username: str) -> Optional[User]:
        """Get a user from storage."""
        users = self._load_users()
        user_data = users.get(username)
        
        if not user_data:
            return None
        
        return User(
            username=user_data["username"],
            email=user_data["email"],
            hashed_password=user_data["hashed_password"],
            role=user_data["role"],
            full_name=user_data["full_name"],
            disabled=user_data["disabled"]
        )

    def get_all_users(self) -> Dict[str, User]:
        """Get all users from storage."""
        users = {}
        for username, user_data in self._load_users().items():
            users[username] = User(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=user_data["hashed_password"],
                role=user_data["role"],
                full_name=user_data["full_name"],
                disabled=user_data["disabled"]
            )
        return users

    def delete_user(self, username: str) -> bool:
        """Delete a user from storage."""
        users = self._load_users()
        if username in users:
            del users[username]
            self._save_users(users)
            return True
        return False

# Create a singleton instance
user_storage = UserStorage()
