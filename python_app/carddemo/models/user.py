"""
User data model for authentication.

This module defines the User model corresponding to the COBOL SEC-USER-DATA
structure defined in CSUSR01Y.cpy (record length 80 bytes).
"""

from dataclasses import dataclass
from enum import Enum


class UserType(Enum):
    """User type enumeration."""

    ADMIN = "A"
    USER = "U"


@dataclass
class User:
    """
    User entity for authentication and authorization.

    Corresponds to COBOL copybook CSUSR01Y.cpy:
    - SEC-USR-ID: User ID (8 chars)
    - SEC-USR-FNAME: First name (20 chars)
    - SEC-USR-LNAME: Last name (20 chars)
    - SEC-USR-PWD: Password (8 chars)
    - SEC-USR-TYPE: User type (A=Admin, U=User)
    """

    user_id: str  # 8-character user ID
    first_name: str = ""
    last_name: str = ""
    password: str = ""  # In production, this should be hashed
    user_type: str = "U"  # A = Admin, U = User

    def __post_init__(self):
        """Validate and normalize user data."""
        # Ensure user_id is uppercase and 8 characters
        self.user_id = str(self.user_id).upper().ljust(8)[:8]
        # Limit field lengths
        self.first_name = str(self.first_name)[:20]
        self.last_name = str(self.last_name)[:20]
        # Ensure password is 8 characters max
        self.password = str(self.password)[:8]
        # Validate user type
        if self.user_type not in ("A", "U"):
            self.user_type = "U"

    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.user_type == "A"

    @property
    def full_name(self) -> str:
        """Get full name."""
        return f"{self.first_name.strip()} {self.last_name.strip()}".strip()

    def verify_password(self, password: str) -> bool:
        """
        Verify password.

        In a production system, this would compare hashed passwords.
        For this demo, we do a simple comparison.
        """
        return self.password.upper() == password.upper()

    def to_dict(self, include_password: bool = False) -> dict:
        """Convert user to dictionary."""
        result = {
            "user_id": self.user_id.strip(),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "user_type": self.user_type,
            "is_admin": self.is_admin,
        }
        if include_password:
            result["password"] = self.password
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create User from dictionary."""
        return cls(
            user_id=data.get("user_id", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            password=data.get("password", ""),
            user_type=data.get("user_type", "U"),
        )


@dataclass
class CardXref:
    """
    Card cross-reference entity.

    Links cards to customers and accounts.
    Corresponds to COBOL copybook CVACT03Y.cpy.
    """

    card_num: str  # 16-character card number
    cust_id: str  # 9-digit customer ID
    acct_id: str  # 11-digit account ID

    def __post_init__(self):
        """Validate and normalize data."""
        self.card_num = str(self.card_num).ljust(16)[:16]
        self.cust_id = str(self.cust_id).zfill(9)[:9]
        self.acct_id = str(self.acct_id).zfill(11)[:11]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "card_num": self.card_num,
            "cust_id": self.cust_id,
            "acct_id": self.acct_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CardXref":
        """Create from dictionary."""
        return cls(
            card_num=data.get("card_num", ""),
            cust_id=data.get("cust_id", ""),
            acct_id=data.get("acct_id", ""),
        )
