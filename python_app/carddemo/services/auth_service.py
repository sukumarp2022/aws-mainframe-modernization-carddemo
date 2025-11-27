"""
Authentication service for CardDemo.

This module provides authentication and authorization functionality,
replacing the COBOL signon screen (COSGN00C) logic.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import secrets

from ..models.user import User
from .data_store import get_data_store


@dataclass
class AuthSession:
    """User authentication session."""

    user_id: str
    user_type: str
    token: str
    created_at: datetime
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now() > self.expires_at

    @property
    def is_admin(self) -> bool:
        """Check if session user is admin."""
        return self.user_type == "A"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id.strip(),
            "user_type": self.user_type,
            "token": self.token,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_admin": self.is_admin,
        }


class AuthService:
    """
    Authentication service.

    Provides login/logout functionality and session management.
    Replaces the COBOL COSGN00C program logic.
    """

    # Session timeout in hours
    SESSION_TIMEOUT_HOURS = 8

    def __init__(self):
        """Initialize the auth service."""
        self._sessions: dict[str, AuthSession] = {}
        self._data_store = get_data_store()

    def login(self, user_id: str, password: str) -> tuple[bool, Optional[AuthSession], str]:
        """
        Authenticate a user.

        Args:
            user_id: User ID
            password: Password

        Returns:
            Tuple of (success, session, message)
        """
        # Normalize user ID
        user_id = str(user_id).upper().strip()

        if not user_id:
            return False, None, "Please enter User ID..."

        if not password:
            return False, None, "Please enter Password..."

        # Look up user
        user = self._data_store.get_user(user_id)
        if user is None:
            return False, None, "User not found. Try again..."

        # Verify password
        if not user.verify_password(password):
            return False, None, "Wrong Password. Try again..."

        # Create session
        session = self._create_session(user)
        return True, session, "Login successful"

    def _create_session(self, user: User) -> AuthSession:
        """Create a new authentication session."""
        token = secrets.token_urlsafe(32)
        now = datetime.now()
        session = AuthSession(
            user_id=user.user_id,
            user_type=user.user_type,
            token=token,
            created_at=now,
            expires_at=now + timedelta(hours=self.SESSION_TIMEOUT_HOURS),
        )
        self._sessions[token] = session
        return session

    def logout(self, token: str) -> bool:
        """
        Log out a user session.

        Args:
            token: Session token

        Returns:
            True if session was found and removed
        """
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False

    def validate_session(self, token: str) -> Optional[AuthSession]:
        """
        Validate a session token.

        Args:
            token: Session token

        Returns:
            AuthSession if valid, None otherwise
        """
        session = self._sessions.get(token)
        if session is None:
            return None
        if session.is_expired:
            del self._sessions[token]
            return None
        return session

    def require_admin(self, token: str) -> tuple[bool, str]:
        """
        Check if session has admin privileges.

        Args:
            token: Session token

        Returns:
            Tuple of (is_admin, message)
        """
        session = self.validate_session(token)
        if session is None:
            return False, "Session not found or expired"
        if not session.is_admin:
            return False, "No access - Admin Only option..."
        return True, "Access granted"

    def get_current_user(self, token: str) -> Optional[User]:
        """
        Get the current user from session token.

        Args:
            token: Session token

        Returns:
            User if session is valid, None otherwise
        """
        session = self.validate_session(token)
        if session is None:
            return None
        return self._data_store.get_user(session.user_id)


# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the global auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
