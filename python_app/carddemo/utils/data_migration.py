"""
Data migration utility.

This module provides utilities for migrating data from the original
mainframe flat files to the new JSON format.
"""

import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any

from ..models.account import Account
from ..models.card import Card
from ..models.customer import Customer
from ..models.user import User, CardXref


def parse_mainframe_date(date_str: str) -> date | None:
    """Parse a mainframe date string (YYYY-MM-DD format)."""
    if not date_str or date_str.strip() == "":
        return None
    try:
        return date.fromisoformat(date_str.strip())
    except ValueError:
        return None


def parse_signed_decimal(value: str) -> Decimal:
    """
    Parse a signed decimal from mainframe format.

    Mainframe signed numerics use { for +0, } for -0, etc.
    The format PIC S9(10)V99 stores 12 digits with implied decimal.
    """
    if not value:
        return Decimal("0.00")

    value = value.strip()

    # Handle signed format with trailing sign character
    sign_chars = {
        "{": ("0", 1),
        "A": ("1", 1),
        "B": ("2", 1),
        "C": ("3", 1),
        "D": ("4", 1),
        "E": ("5", 1),
        "F": ("6", 1),
        "G": ("7", 1),
        "H": ("8", 1),
        "I": ("9", 1),
        "}": ("0", -1),
        "J": ("1", -1),
        "K": ("2", -1),
        "L": ("3", -1),
        "M": ("4", -1),
        "N": ("5", -1),
        "O": ("6", -1),
        "P": ("7", -1),
        "Q": ("8", -1),
        "R": ("9", -1),
    }

    if value[-1] in sign_chars:
        digit, sign = sign_chars[value[-1]]
        value = value[:-1] + digit
    else:
        sign = 1

    # Remove any non-digit characters
    value = "".join(c for c in value if c.isdigit())

    if not value:
        return Decimal("0.00")

    # Insert decimal point (last 2 digits are cents)
    if len(value) > 2:
        value = value[:-2] + "." + value[-2:]
    else:
        value = "0." + value.zfill(2)

    return Decimal(value) * sign


def parse_account_record(line: str) -> Account:
    """
    Parse an account record from mainframe format.

    CVACT01Y.cpy record layout (300 bytes):
    - ACCT-ID: 11 digits (positions 1-11)
    - ACCT-ACTIVE-STATUS: 1 char (position 12)
    - ACCT-CURR-BAL: S9(10)V99 (positions 13-25, 13 chars)
    - ACCT-CREDIT-LIMIT: S9(10)V99 (positions 26-38, 13 chars)
    - ACCT-CASH-CREDIT-LIMIT: S9(10)V99 (positions 39-51, 13 chars)
    - ACCT-OPEN-DATE: X(10) (positions 52-61)
    - ACCT-EXPIRAION-DATE: X(10) (positions 62-71)
    - ACCT-REISSUE-DATE: X(10) (positions 72-81)
    - ACCT-CURR-CYC-CREDIT: S9(10)V99 (positions 82-94, 13 chars)
    - ACCT-CURR-CYC-DEBIT: S9(10)V99 (positions 95-107, 13 chars)
    - ACCT-ADDR-ZIP: X(10) (positions 108-117)
    - ACCT-GROUP-ID: X(10) (positions 118-127)
    - FILLER: X(178) (positions 128-300)
    """
    return Account(
        acct_id=line[0:11].strip(),
        active_status=line[11:12].strip() or "Y",
        curr_bal=parse_signed_decimal(line[12:25]),
        credit_limit=parse_signed_decimal(line[25:38]),
        cash_credit_limit=parse_signed_decimal(line[38:51]),
        open_date=parse_mainframe_date(line[51:61]),
        expiration_date=parse_mainframe_date(line[61:71]),
        reissue_date=parse_mainframe_date(line[71:81]),
        curr_cyc_credit=parse_signed_decimal(line[81:94]),
        curr_cyc_debit=parse_signed_decimal(line[94:107]),
        addr_zip=line[107:117].strip(),
        group_id=line[117:127].strip(),
    )


def parse_card_record(line: str) -> Card:
    """
    Parse a card record from mainframe format.

    CVACT02Y.cpy record layout (150 bytes):
    - CARD-NUM: X(16) (positions 1-16)
    - CARD-ACCT-ID: 9(11) (positions 17-27)
    - CARD-CVV-CD: 9(03) (positions 28-30)
    - CARD-EMBOSSED-NAME: X(50) (positions 31-80)
    - CARD-EXPIRAION-DATE: X(10) (positions 81-90)
    - CARD-ACTIVE-STATUS: X(01) (position 91)
    - FILLER: X(59) (positions 92-150)
    """
    return Card(
        card_num=line[0:16].strip(),
        acct_id=line[16:27].strip(),
        cvv_cd=line[27:30].strip(),
        embossed_name=line[30:80].strip(),
        expiration_date=parse_mainframe_date(line[80:90]),
        active_status=line[90:91].strip() or "Y",
    )


def parse_customer_record(line: str) -> Customer:
    """
    Parse a customer record from mainframe format.

    CVCUS01Y.cpy record layout (500 bytes):
    - CUST-ID: 9(09) (positions 1-9)
    - CUST-FIRST-NAME: X(25) (positions 10-34)
    - CUST-MIDDLE-NAME: X(25) (positions 35-59)
    - CUST-LAST-NAME: X(25) (positions 60-84)
    - CUST-ADDR-LINE-1: X(50) (positions 85-134)
    - CUST-ADDR-LINE-2: X(50) (positions 135-184)
    - CUST-ADDR-LINE-3: X(50) (positions 185-234)
    - CUST-ADDR-STATE-CD: X(02) (positions 235-236)
    - CUST-ADDR-COUNTRY-CD: X(03) (positions 237-239)
    - CUST-ADDR-ZIP: X(10) (positions 240-249)
    - CUST-PHONE-NUM-1: X(15) (positions 250-264)
    - CUST-PHONE-NUM-2: X(15) (positions 265-279)
    - CUST-SSN: 9(09) (positions 280-288)
    - CUST-GOVT-ISSUED-ID: X(20) (positions 289-308)
    - CUST-DOB-YYYY-MM-DD: X(10) (positions 309-318)
    - CUST-EFT-ACCOUNT-ID: X(10) (positions 319-328)
    - CUST-PRI-CARD-HOLDER-IND: X(01) (position 329)
    - CUST-FICO-CREDIT-SCORE: 9(03) (positions 330-332)
    - FILLER: X(168) (positions 333-500)
    """
    return Customer(
        cust_id=line[0:9].strip(),
        first_name=line[9:34].strip(),
        middle_name=line[34:59].strip(),
        last_name=line[59:84].strip(),
        addr_line_1=line[84:134].strip(),
        addr_line_2=line[134:184].strip(),
        addr_line_3=line[184:234].strip(),
        addr_state_cd=line[234:236].strip(),
        addr_country_cd=line[236:239].strip(),
        addr_zip=line[239:249].strip(),
        phone_num_1=line[249:264].strip(),
        phone_num_2=line[264:279].strip(),
        ssn=line[279:288].strip(),
        govt_issued_id=line[288:308].strip(),
        dob=parse_mainframe_date(line[308:318]),
        eft_account_id=line[318:328].strip(),
        pri_card_holder_ind=line[328:329].strip() or "Y",
        fico_credit_score=int(line[329:332]) if line[329:332].strip().isdigit() else 0,
    )


def parse_cardxref_record(line: str) -> CardXref:
    """
    Parse a card cross-reference record from mainframe format.

    CVACT03Y.cpy record layout (50 bytes):
    - XREF-CARD-NUM: X(16) (positions 1-16)
    - XREF-CUST-ID: 9(09) (positions 17-25)
    - XREF-ACCT-ID: 9(11) (positions 26-36)
    - FILLER: X(14) (positions 37-50)
    """
    return CardXref(
        card_num=line[0:16].strip(),
        cust_id=line[16:25].strip(),
        acct_id=line[25:36].strip(),
    )


def migrate_file(
    input_path: str,
    output_path: str,
    record_type: str,
) -> int:
    """
    Migrate a mainframe data file to JSON format.

    Args:
        input_path: Path to mainframe data file (ASCII format)
        output_path: Path to output JSON file
        record_type: Type of record ('account', 'card', 'customer', 'cardxref')

    Returns:
        Number of records migrated
    """
    parsers = {
        "account": parse_account_record,
        "card": parse_card_record,
        "customer": parse_customer_record,
        "cardxref": parse_cardxref_record,
    }

    if record_type not in parsers:
        raise ValueError(f"Unknown record type: {record_type}")

    parser = parsers[record_type]
    records = []

    with open(input_path, "r") as f:
        for line in f:
            if line.strip():
                record = parser(line.rstrip("\n"))
                records.append(record.to_dict())

    with open(output_path, "w") as f:
        json.dump(records, f, indent=2)

    return len(records)


def create_sample_users() -> List[Dict[str, Any]]:
    """Create sample user data."""
    users = [
        User(
            user_id="ADMIN001",
            first_name="Admin",
            last_name="User",
            password="PASSWORD",
            user_type="A",
        ),
        User(
            user_id="USER0001",
            first_name="Regular",
            last_name="User",
            password="PASSWORD",
            user_type="U",
        ),
    ]
    return [u.to_dict(include_password=True) for u in users]


def migrate_all(source_dir: str, target_dir: str) -> Dict[str, int]:
    """
    Migrate all mainframe data files to JSON format.

    Args:
        source_dir: Directory containing mainframe ASCII data files
        target_dir: Directory to write JSON files

    Returns:
        Dictionary of file counts
    """
    Path(target_dir).mkdir(parents=True, exist_ok=True)

    file_mappings = [
        ("acctdata.txt", "accounts.json", "account"),
        ("carddata.txt", "cards.json", "card"),
        ("custdata.txt", "customers.json", "customer"),
        ("cardxref.txt", "cardxref.json", "cardxref"),
    ]

    results = {}

    for source_file, target_file, record_type in file_mappings:
        source_path = os.path.join(source_dir, source_file)
        target_path = os.path.join(target_dir, target_file)

        if os.path.exists(source_path):
            count = migrate_file(source_path, target_path, record_type)
            results[source_file] = count
            print(f"Migrated {count} records from {source_file} to {target_file}")
        else:
            print(f"Source file not found: {source_path}")

    # Create users file
    users_path = os.path.join(target_dir, "users.json")
    users = create_sample_users()
    with open(users_path, "w") as f:
        json.dump(users, f, indent=2)
    results["users.json"] = len(users)
    print(f"Created {len(users)} sample users")

    # Create empty transactions file
    transactions_path = os.path.join(target_dir, "transactions.json")
    with open(transactions_path, "w") as f:
        json.dump([], f, indent=2)
    results["transactions.json"] = 0
    print("Created empty transactions file")

    return results


def main():
    """Main entry point for data migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate mainframe data to JSON format")
    parser.add_argument(
        "--source",
        required=True,
        help="Source directory containing mainframe ASCII data files",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target directory for JSON files",
    )

    args = parser.parse_args()

    results = migrate_all(args.source, args.target)

    print("\nMigration complete!")
    print(f"Total records migrated: {sum(results.values())}")


if __name__ == "__main__":
    main()
