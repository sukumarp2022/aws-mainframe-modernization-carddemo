"""
Transaction data model.

This module defines the Transaction model corresponding to the COBOL TRAN-RECORD
structure defined in CVTRA05Y.cpy (record length 350 bytes).
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Transaction:
    """
    Transaction entity.

    Corresponds to COBOL copybook CVTRA05Y.cpy:
    - TRAN-ID: 16-character transaction ID
    - TRAN-TYPE-CD: 2-character transaction type code
    - TRAN-CAT-CD: 4-digit category code
    - TRAN-SOURCE: Transaction source
    - TRAN-DESC: Transaction description
    - TRAN-AMT: Transaction amount
    - TRAN-MERCHANT-ID: Merchant ID
    - TRAN-MERCHANT-NAME: Merchant name
    - TRAN-MERCHANT-CITY: Merchant city
    - TRAN-MERCHANT-ZIP: Merchant ZIP code
    - TRAN-CARD-NUM: Card number
    - TRAN-ORIG-TS: Origination timestamp
    - TRAN-PROC-TS: Processing timestamp
    """

    tran_id: str  # 16-character transaction ID
    type_cd: str = "01"  # 2-character type code
    cat_cd: str = "0000"  # 4-digit category code
    source: str = ""  # Transaction source
    description: str = ""  # Transaction description
    amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    merchant_id: str = ""
    merchant_name: str = ""
    merchant_city: str = ""
    merchant_zip: str = ""
    card_num: str = ""  # 16-character card number
    orig_ts: Optional[datetime] = None  # Origination timestamp
    proc_ts: Optional[datetime] = None  # Processing timestamp

    def __post_init__(self):
        """Validate and normalize transaction data."""
        # Ensure tran_id is 16 characters
        self.tran_id = str(self.tran_id).ljust(16)[:16]
        # Ensure type_cd is 2 characters
        self.type_cd = str(self.type_cd).zfill(2)[:2]
        # Ensure cat_cd is 4 digits
        self.cat_cd = str(self.cat_cd).zfill(4)[:4]
        # Ensure card_num is 16 characters
        self.card_num = str(self.card_num).ljust(16)[:16]
        # Ensure decimal amount
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))
        # Set processing timestamp if not provided
        if self.proc_ts is None:
            self.proc_ts = datetime.now()
        if self.orig_ts is None:
            self.orig_ts = self.proc_ts

    @property
    def is_credit(self) -> bool:
        """Check if transaction is a credit (negative amount)."""
        return self.amount < 0

    @property
    def is_debit(self) -> bool:
        """Check if transaction is a debit (positive amount)."""
        return self.amount >= 0

    @property
    def formatted_amount(self) -> str:
        """Get formatted amount with currency symbol."""
        return f"${abs(self.amount):,.2f}"

    def to_dict(self) -> dict:
        """Convert transaction to dictionary."""
        return {
            "tran_id": self.tran_id,
            "type_cd": self.type_cd,
            "cat_cd": self.cat_cd,
            "source": self.source,
            "description": self.description,
            "amount": str(self.amount),
            "formatted_amount": self.formatted_amount,
            "merchant_id": self.merchant_id,
            "merchant_name": self.merchant_name,
            "merchant_city": self.merchant_city,
            "merchant_zip": self.merchant_zip,
            "card_num": self.card_num,
            "orig_ts": self.orig_ts.isoformat() if self.orig_ts else None,
            "proc_ts": self.proc_ts.isoformat() if self.proc_ts else None,
            "is_credit": self.is_credit,
            "is_debit": self.is_debit,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        """Create Transaction from dictionary."""
        return cls(
            tran_id=data.get("tran_id", ""),
            type_cd=data.get("type_cd", "01"),
            cat_cd=data.get("cat_cd", "0000"),
            source=data.get("source", ""),
            description=data.get("description", ""),
            amount=Decimal(data.get("amount", "0")),
            merchant_id=data.get("merchant_id", ""),
            merchant_name=data.get("merchant_name", ""),
            merchant_city=data.get("merchant_city", ""),
            merchant_zip=data.get("merchant_zip", ""),
            card_num=data.get("card_num", ""),
            orig_ts=(
                datetime.fromisoformat(data["orig_ts"]) if data.get("orig_ts") else None
            ),
            proc_ts=(
                datetime.fromisoformat(data["proc_ts"]) if data.get("proc_ts") else None
            ),
        )


@dataclass
class TransactionType:
    """
    Transaction Type reference data.

    Corresponds to COBOL copybook CVTRA03Y.cpy.
    """

    type_cd: str  # 2-character type code
    type_desc: str = ""  # Type description

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "type_cd": self.type_cd,
            "type_desc": self.type_desc,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TransactionType":
        """Create from dictionary."""
        return cls(
            type_cd=data.get("type_cd", ""),
            type_desc=data.get("type_desc", ""),
        )


@dataclass
class TransactionCategory:
    """
    Transaction Category reference data.

    Corresponds to COBOL copybook CVTRA04Y.cpy.
    """

    cat_cd: str  # 4-digit category code
    cat_desc: str = ""  # Category description

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "cat_cd": self.cat_cd,
            "cat_desc": self.cat_desc,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TransactionCategory":
        """Create from dictionary."""
        return cls(
            cat_cd=data.get("cat_cd", ""),
            cat_desc=data.get("cat_desc", ""),
        )
