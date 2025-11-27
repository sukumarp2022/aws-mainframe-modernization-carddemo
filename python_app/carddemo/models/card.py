"""
Card data model.

This module defines the Card model corresponding to the COBOL CARD-RECORD
structure defined in CVACT02Y.cpy (record length 150 bytes).
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Card:
    """
    Credit Card entity.

    Corresponds to COBOL copybook CVACT02Y.cpy:
    - CARD-NUM: 16-character card number
    - CARD-ACCT-ID: 11-digit account ID
    - CARD-CVV-CD: 3-digit CVV code
    - CARD-EMBOSSED-NAME: Cardholder name (50 chars)
    - CARD-EXPIRAION-DATE: Card expiration date
    - CARD-ACTIVE-STATUS: Active status flag (Y/N)
    """

    card_num: str  # 16-character card number
    acct_id: str  # 11-digit account ID
    cvv_cd: str = "000"  # 3-digit CVV
    embossed_name: str = ""  # Cardholder name
    expiration_date: Optional[date] = None
    active_status: str = "Y"  # Y = Active, N = Inactive

    def __post_init__(self):
        """Validate and normalize card data."""
        # Ensure card_num is 16 characters
        self.card_num = str(self.card_num).ljust(16)[:16]
        # Ensure acct_id is 11 characters, zero-padded
        self.acct_id = str(self.acct_id).zfill(11)[:11]
        # Ensure CVV is 3 digits
        self.cvv_cd = str(self.cvv_cd).zfill(3)[:3]
        # Limit embossed name to 50 characters
        self.embossed_name = str(self.embossed_name)[:50]

    @property
    def is_active(self) -> bool:
        """Check if card is active."""
        return self.active_status == "Y"

    @property
    def is_expired(self) -> bool:
        """Check if card is expired."""
        if self.expiration_date is None:
            return False
        return date.today() > self.expiration_date

    @property
    def masked_card_num(self) -> str:
        """Return masked card number (show last 4 digits only)."""
        return "*" * 12 + self.card_num[-4:]

    def to_dict(self) -> dict:
        """Convert card to dictionary."""
        return {
            "card_num": self.card_num,
            "masked_card_num": self.masked_card_num,
            "acct_id": self.acct_id,
            "cvv_cd": self.cvv_cd,
            "embossed_name": self.embossed_name,
            "expiration_date": (
                self.expiration_date.isoformat() if self.expiration_date else None
            ),
            "active_status": self.active_status,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Card":
        """Create Card from dictionary."""
        return cls(
            card_num=data.get("card_num", ""),
            acct_id=data.get("acct_id", ""),
            cvv_cd=data.get("cvv_cd", "000"),
            embossed_name=data.get("embossed_name", ""),
            expiration_date=(
                date.fromisoformat(data["expiration_date"])
                if data.get("expiration_date")
                else None
            ),
            active_status=data.get("active_status", "Y"),
        )
