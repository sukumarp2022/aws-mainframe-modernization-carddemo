"""
Account data model.

This module defines the Account model corresponding to the COBOL ACCOUNT-RECORD
structure defined in CVACT01Y.cpy (record length 300 bytes).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class Account:
    """
    Account entity representing a credit card account.

    Corresponds to COBOL copybook CVACT01Y.cpy:
    - ACCT-ID: 11-digit account identifier
    - ACCT-ACTIVE-STATUS: Active status flag (Y/N)
    - ACCT-CURR-BAL: Current balance
    - ACCT-CREDIT-LIMIT: Credit limit
    - ACCT-CASH-CREDIT-LIMIT: Cash credit limit
    - ACCT-OPEN-DATE: Account open date
    - ACCT-EXPIRAION-DATE: Account expiration date
    - ACCT-REISSUE-DATE: Reissue date
    - ACCT-CURR-CYC-CREDIT: Current cycle credit
    - ACCT-CURR-CYC-DEBIT: Current cycle debit
    - ACCT-ADDR-ZIP: Address ZIP code
    - ACCT-GROUP-ID: Account group ID
    """

    acct_id: str  # 11-digit account ID
    active_status: str = "Y"  # Y = Active, N = Inactive
    curr_bal: Decimal = field(default_factory=lambda: Decimal("0.00"))
    credit_limit: Decimal = field(default_factory=lambda: Decimal("0.00"))
    cash_credit_limit: Decimal = field(default_factory=lambda: Decimal("0.00"))
    open_date: Optional[date] = None
    expiration_date: Optional[date] = None
    reissue_date: Optional[date] = None
    curr_cyc_credit: Decimal = field(default_factory=lambda: Decimal("0.00"))
    curr_cyc_debit: Decimal = field(default_factory=lambda: Decimal("0.00"))
    addr_zip: str = ""
    group_id: str = ""

    def __post_init__(self):
        """Validate and normalize account data."""
        # Ensure acct_id is 11 characters, zero-padded
        self.acct_id = str(self.acct_id).zfill(11)[:11]

        # Ensure decimal values
        if not isinstance(self.curr_bal, Decimal):
            self.curr_bal = Decimal(str(self.curr_bal))
        if not isinstance(self.credit_limit, Decimal):
            self.credit_limit = Decimal(str(self.credit_limit))
        if not isinstance(self.cash_credit_limit, Decimal):
            self.cash_credit_limit = Decimal(str(self.cash_credit_limit))
        if not isinstance(self.curr_cyc_credit, Decimal):
            self.curr_cyc_credit = Decimal(str(self.curr_cyc_credit))
        if not isinstance(self.curr_cyc_debit, Decimal):
            self.curr_cyc_debit = Decimal(str(self.curr_cyc_debit))

    @property
    def available_credit(self) -> Decimal:
        """Calculate available credit."""
        return self.credit_limit - self.curr_bal

    @property
    def is_active(self) -> bool:
        """Check if account is active."""
        return self.active_status == "Y"

    @property
    def is_overlimit(self) -> bool:
        """Check if account is over credit limit."""
        return self.curr_bal > self.credit_limit

    def to_dict(self) -> dict:
        """Convert account to dictionary."""
        return {
            "acct_id": self.acct_id,
            "active_status": self.active_status,
            "curr_bal": str(self.curr_bal),
            "credit_limit": str(self.credit_limit),
            "cash_credit_limit": str(self.cash_credit_limit),
            "open_date": self.open_date.isoformat() if self.open_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "reissue_date": self.reissue_date.isoformat() if self.reissue_date else None,
            "curr_cyc_credit": str(self.curr_cyc_credit),
            "curr_cyc_debit": str(self.curr_cyc_debit),
            "addr_zip": self.addr_zip,
            "group_id": self.group_id,
            "available_credit": str(self.available_credit),
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Account":
        """Create Account from dictionary."""
        return cls(
            acct_id=data.get("acct_id", ""),
            active_status=data.get("active_status", "Y"),
            curr_bal=Decimal(data.get("curr_bal", "0")),
            credit_limit=Decimal(data.get("credit_limit", "0")),
            cash_credit_limit=Decimal(data.get("cash_credit_limit", "0")),
            open_date=(
                date.fromisoformat(data["open_date"]) if data.get("open_date") else None
            ),
            expiration_date=(
                date.fromisoformat(data["expiration_date"])
                if data.get("expiration_date")
                else None
            ),
            reissue_date=(
                date.fromisoformat(data["reissue_date"]) if data.get("reissue_date") else None
            ),
            curr_cyc_credit=Decimal(data.get("curr_cyc_credit", "0")),
            curr_cyc_debit=Decimal(data.get("curr_cyc_debit", "0")),
            addr_zip=data.get("addr_zip", ""),
            group_id=data.get("group_id", ""),
        )
