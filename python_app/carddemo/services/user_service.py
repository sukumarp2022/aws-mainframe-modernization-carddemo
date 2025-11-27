"""
User management service for CardDemo.

This module provides user management functionality for admin users,
replacing the COBOL user programs (COUSR00C, COUSR01C, COUSR02C, COUSR03C).
"""

from typing import List, Optional, Tuple

from ..models.user import User
from .data_store import get_data_store


class UserService:
    """
    User management service.

    Provides user CRUD operations for admin users.
    Replaces COBOL programs:
    - COUSR00C: List users
    - COUSR01C: Add user
    - COUSR02C: Update user
    - COUSR03C: Delete user
    """

    def __init__(self):
        """Initialize the user service."""
        self._data_store = get_data_store()

    def list_users(
        self,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[User], int]:
        """
        List users with pagination.

        Args:
            page: Page number (1-based)
            page_size: Number of records per page

        Returns:
            Tuple of (users, total_count)
        """
        users = self._data_store.get_users()
        total = len(users)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        users = users[start:end]

        return users, total

    def get_user(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User if found, None otherwise
        """
        return self._data_store.get_user(user_id)

    def add_user(
        self,
        user_id: str,
        password: str,
        first_name: str,
        last_name: str,
        user_type: str = "U",
    ) -> Tuple[bool, str]:
        """
        Add a new user.

        Args:
            user_id: User ID (max 8 characters)
            password: Password (max 8 characters)
            first_name: First name
            last_name: Last name
            user_type: User type (A=Admin, U=User)

        Returns:
            Tuple of (success, message)
        """
        # Validate inputs
        if not user_id or not user_id.strip():
            return False, "User ID is required"

        if not password or not password.strip():
            return False, "Password is required"

        if len(user_id) > 8:
            return False, "User ID cannot exceed 8 characters"

        if len(password) > 8:
            return False, "Password cannot exceed 8 characters"

        if user_type not in ("A", "U"):
            return False, "User type must be A (Admin) or U (User)"

        # Check if user already exists
        existing = self._data_store.get_user(user_id)
        if existing is not None:
            return False, "User ID already exists"

        # Create user
        user = User(
            user_id=user_id,
            password=password.upper(),
            first_name=first_name,
            last_name=last_name,
            user_type=user_type,
        )

        self._data_store.save_user(user)
        return True, "User created successfully"

    def update_user(
        self,
        user_id: str,
        password: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        user_type: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Update a user.

        Args:
            user_id: User ID
            password: New password (optional)
            first_name: New first name (optional)
            last_name: New last name (optional)
            user_type: New user type (optional)

        Returns:
            Tuple of (success, message)
        """
        user = self._data_store.get_user(user_id)
        if user is None:
            return False, "User not found"

        if password is not None:
            if len(password) > 8:
                return False, "Password cannot exceed 8 characters"
            user.password = password.upper()

        if first_name is not None:
            user.first_name = first_name[:20]

        if last_name is not None:
            user.last_name = last_name[:20]

        if user_type is not None:
            if user_type not in ("A", "U"):
                return False, "User type must be A (Admin) or U (User)"
            user.user_type = user_type

        self._data_store.save_user(user)
        return True, "User updated successfully"

    def delete_user(self, user_id: str) -> Tuple[bool, str]:
        """
        Delete a user.

        Args:
            user_id: User ID

        Returns:
            Tuple of (success, message)
        """
        user = self._data_store.get_user(user_id)
        if user is None:
            return False, "User not found"

        if self._data_store.delete_user(user_id):
            return True, "User deleted successfully"
        return False, "Failed to delete user"


# Global service instance
_user_service: Optional[UserService] = None


def get_user_service() -> UserService:
    """Get the global user service instance."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
