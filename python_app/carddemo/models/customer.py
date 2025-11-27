"""
Customer data model.

This module defines the Customer model corresponding to the COBOL CUSTOMER-RECORD
structure defined in CVCUS01Y.cpy (record length 500 bytes).
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Customer:
    """
    Customer entity.

    Corresponds to COBOL copybook CVCUS01Y.cpy:
    - CUST-ID: 9-digit customer ID
    - CUST-FIRST-NAME: First name (25 chars)
    - CUST-MIDDLE-NAME: Middle name (25 chars)
    - CUST-LAST-NAME: Last name (25 chars)
    - CUST-ADDR-LINE-1/2/3: Address lines (50 chars each)
    - CUST-ADDR-STATE-CD: State code (2 chars)
    - CUST-ADDR-COUNTRY-CD: Country code (3 chars)
    - CUST-ADDR-ZIP: ZIP code (10 chars)
    - CUST-PHONE-NUM-1/2: Phone numbers (15 chars each)
    - CUST-SSN: Social Security Number (9 digits)
    - CUST-GOVT-ISSUED-ID: Government ID (20 chars)
    - CUST-DOB-YYYY-MM-DD: Date of birth
    - CUST-EFT-ACCOUNT-ID: EFT account ID (10 chars)
    - CUST-PRI-CARD-HOLDER-IND: Primary cardholder indicator
    - CUST-FICO-CREDIT-SCORE: FICO credit score (3 digits)
    """

    cust_id: str  # 9-digit customer ID
    first_name: str = ""
    middle_name: str = ""
    last_name: str = ""
    addr_line_1: str = ""
    addr_line_2: str = ""
    addr_line_3: str = ""
    addr_state_cd: str = ""
    addr_country_cd: str = "USA"
    addr_zip: str = ""
    phone_num_1: str = ""
    phone_num_2: str = ""
    ssn: str = ""  # 9-digit SSN (stored encrypted in production)
    govt_issued_id: str = ""
    dob: Optional[date] = None
    eft_account_id: str = ""
    pri_card_holder_ind: str = "Y"  # Y = Primary, N = Secondary
    fico_credit_score: int = 0

    def __post_init__(self):
        """Validate and normalize customer data."""
        # Ensure cust_id is 9 characters, zero-padded
        self.cust_id = str(self.cust_id).zfill(9)[:9]
        # Limit field lengths
        self.first_name = str(self.first_name)[:25]
        self.middle_name = str(self.middle_name)[:25]
        self.last_name = str(self.last_name)[:25]
        self.addr_line_1 = str(self.addr_line_1)[:50]
        self.addr_line_2 = str(self.addr_line_2)[:50]
        self.addr_line_3 = str(self.addr_line_3)[:50]
        self.addr_state_cd = str(self.addr_state_cd)[:2].upper()
        self.addr_country_cd = str(self.addr_country_cd)[:3].upper()
        self.addr_zip = str(self.addr_zip)[:10]
        self.phone_num_1 = str(self.phone_num_1)[:15]
        self.phone_num_2 = str(self.phone_num_2)[:15]
        self.ssn = str(self.ssn).zfill(9)[:9]
        self.govt_issued_id = str(self.govt_issued_id)[:20]
        self.eft_account_id = str(self.eft_account_id)[:10]
        # Ensure FICO score is within valid range
        self.fico_credit_score = max(0, min(850, int(self.fico_credit_score)))

    @property
    def full_name(self) -> str:
        """Get full name."""
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p.strip() for p in parts if p.strip())

    @property
    def full_address(self) -> str:
        """Get full address."""
        lines = [self.addr_line_1, self.addr_line_2, self.addr_line_3]
        addr_lines = [line.strip() for line in lines if line.strip()]
        city_state_zip = f"{self.addr_state_cd} {self.addr_country_cd} {self.addr_zip}".strip()
        if city_state_zip:
            addr_lines.append(city_state_zip)
        return ", ".join(addr_lines)

    @property
    def is_primary_cardholder(self) -> bool:
        """Check if customer is primary cardholder."""
        return self.pri_card_holder_ind == "Y"

    @property
    def masked_ssn(self) -> str:
        """Return masked SSN (show last 4 digits only)."""
        return "***-**-" + self.ssn[-4:]

    def to_dict(self) -> dict:
        """Convert customer to dictionary."""
        return {
            "cust_id": self.cust_id,
            "first_name": self.first_name,
            "middle_name": self.middle_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "addr_line_1": self.addr_line_1,
            "addr_line_2": self.addr_line_2,
            "addr_line_3": self.addr_line_3,
            "addr_state_cd": self.addr_state_cd,
            "addr_country_cd": self.addr_country_cd,
            "addr_zip": self.addr_zip,
            "full_address": self.full_address,
            "phone_num_1": self.phone_num_1,
            "phone_num_2": self.phone_num_2,
            "masked_ssn": self.masked_ssn,
            "govt_issued_id": self.govt_issued_id,
            "dob": self.dob.isoformat() if self.dob else None,
            "eft_account_id": self.eft_account_id,
            "pri_card_holder_ind": self.pri_card_holder_ind,
            "is_primary_cardholder": self.is_primary_cardholder,
            "fico_credit_score": self.fico_credit_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Customer":
        """Create Customer from dictionary."""
        return cls(
            cust_id=data.get("cust_id", ""),
            first_name=data.get("first_name", ""),
            middle_name=data.get("middle_name", ""),
            last_name=data.get("last_name", ""),
            addr_line_1=data.get("addr_line_1", ""),
            addr_line_2=data.get("addr_line_2", ""),
            addr_line_3=data.get("addr_line_3", ""),
            addr_state_cd=data.get("addr_state_cd", ""),
            addr_country_cd=data.get("addr_country_cd", "USA"),
            addr_zip=data.get("addr_zip", ""),
            phone_num_1=data.get("phone_num_1", ""),
            phone_num_2=data.get("phone_num_2", ""),
            ssn=data.get("ssn", ""),
            govt_issued_id=data.get("govt_issued_id", ""),
            dob=date.fromisoformat(data["dob"]) if data.get("dob") else None,
            eft_account_id=data.get("eft_account_id", ""),
            pri_card_holder_ind=data.get("pri_card_holder_ind", "Y"),
            fico_credit_score=int(data.get("fico_credit_score", 0)),
        )
