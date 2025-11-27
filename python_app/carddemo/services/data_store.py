"""
Data store for CardDemo application.

This module provides a JSON-based data store that replaces the VSAM files
from the original mainframe application.
"""

import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, TypeVar

from ..models.account import Account
from ..models.card import Card
from ..models.customer import Customer
from ..models.transaction import Transaction, TransactionType, TransactionCategory
from ..models.user import User, CardXref


T = TypeVar("T")


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for CardDemo data types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


def json_decoder(dct: dict) -> dict:
    """Custom JSON decoder hook."""
    return dct


class DataStore:
    """
    JSON-based data store for CardDemo.

    Replaces VSAM file operations from the mainframe application.
    Provides thread-safe read/write operations.
    """

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the data store.

        Args:
            data_dir: Directory containing data files. Defaults to 'data' subdirectory.
        """
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Thread locks for each data file
        self._locks: Dict[str, Lock] = {}

        # Cache for loaded data
        self._cache: Dict[str, Any] = {}

    def _get_lock(self, name: str) -> Lock:
        """Get or create a lock for a data file."""
        if name not in self._locks:
            self._locks[name] = Lock()
        return self._locks[name]

    def _get_file_path(self, name: str) -> Path:
        """Get the file path for a data store."""
        return self.data_dir / f"{name}.json"

    def _load_file(self, name: str) -> List[dict]:
        """Load data from a JSON file."""
        file_path = self._get_file_path(name)
        if not file_path.exists():
            return []
        with open(file_path, "r") as f:
            return json.load(f, object_hook=json_decoder)

    def _save_file(self, name: str, data: List[dict]) -> None:
        """Save data to a JSON file."""
        file_path = self._get_file_path(name)
        with open(file_path, "w") as f:
            json.dump(data, f, cls=JSONEncoder, indent=2)

    # Account operations
    def get_accounts(self) -> List[Account]:
        """Get all accounts."""
        with self._get_lock("accounts"):
            data = self._load_file("accounts")
            return [Account.from_dict(d) for d in data]

    def get_account(self, acct_id: str) -> Optional[Account]:
        """Get an account by ID."""
        acct_id = str(acct_id).zfill(11)[:11]
        accounts = self.get_accounts()
        for account in accounts:
            if account.acct_id == acct_id:
                return account
        return None

    def save_account(self, account: Account) -> None:
        """Save or update an account."""
        with self._get_lock("accounts"):
            accounts = self._load_file("accounts")
            # Find and update or append
            found = False
            for i, acct in enumerate(accounts):
                if acct.get("acct_id") == account.acct_id:
                    accounts[i] = account.to_dict()
                    found = True
                    break
            if not found:
                accounts.append(account.to_dict())
            self._save_file("accounts", accounts)

    def delete_account(self, acct_id: str) -> bool:
        """Delete an account."""
        acct_id = str(acct_id).zfill(11)[:11]
        with self._get_lock("accounts"):
            accounts = self._load_file("accounts")
            new_accounts = [a for a in accounts if a.get("acct_id") != acct_id]
            if len(new_accounts) < len(accounts):
                self._save_file("accounts", new_accounts)
                return True
            return False

    # Card operations
    def get_cards(self) -> List[Card]:
        """Get all cards."""
        with self._get_lock("cards"):
            data = self._load_file("cards")
            return [Card.from_dict(d) for d in data]

    def get_card(self, card_num: str) -> Optional[Card]:
        """Get a card by number."""
        card_num = str(card_num).ljust(16)[:16]
        cards = self.get_cards()
        for card in cards:
            if card.card_num == card_num:
                return card
        return None

    def get_cards_by_account(self, acct_id: str) -> List[Card]:
        """Get all cards for an account."""
        acct_id = str(acct_id).zfill(11)[:11]
        cards = self.get_cards()
        return [card for card in cards if card.acct_id == acct_id]

    def save_card(self, card: Card) -> None:
        """Save or update a card."""
        with self._get_lock("cards"):
            cards = self._load_file("cards")
            found = False
            for i, c in enumerate(cards):
                if c.get("card_num") == card.card_num:
                    cards[i] = card.to_dict()
                    found = True
                    break
            if not found:
                cards.append(card.to_dict())
            self._save_file("cards", cards)

    # Customer operations
    def get_customers(self) -> List[Customer]:
        """Get all customers."""
        with self._get_lock("customers"):
            data = self._load_file("customers")
            return [Customer.from_dict(d) for d in data]

    def get_customer(self, cust_id: str) -> Optional[Customer]:
        """Get a customer by ID."""
        cust_id = str(cust_id).zfill(9)[:9]
        customers = self.get_customers()
        for customer in customers:
            if customer.cust_id == cust_id:
                return customer
        return None

    def save_customer(self, customer: Customer) -> None:
        """Save or update a customer."""
        with self._get_lock("customers"):
            customers = self._load_file("customers")
            found = False
            for i, c in enumerate(customers):
                if c.get("cust_id") == customer.cust_id:
                    customers[i] = customer.to_dict()
                    found = True
                    break
            if not found:
                customers.append(customer.to_dict())
            self._save_file("customers", customers)

    # Transaction operations
    def get_transactions(self, card_num: Optional[str] = None) -> List[Transaction]:
        """Get all transactions, optionally filtered by card number."""
        with self._get_lock("transactions"):
            data = self._load_file("transactions")
            transactions = [Transaction.from_dict(d) for d in data]
            if card_num:
                card_num = str(card_num).ljust(16)[:16]
                transactions = [t for t in transactions if t.card_num == card_num]
            return transactions

    def get_transaction(self, tran_id: str) -> Optional[Transaction]:
        """Get a transaction by ID."""
        tran_id = str(tran_id).ljust(16)[:16]
        transactions = self.get_transactions()
        for transaction in transactions:
            if transaction.tran_id == tran_id:
                return transaction
        return None

    def save_transaction(self, transaction: Transaction) -> None:
        """Save or update a transaction."""
        with self._get_lock("transactions"):
            transactions = self._load_file("transactions")
            found = False
            for i, t in enumerate(transactions):
                if t.get("tran_id") == transaction.tran_id:
                    transactions[i] = transaction.to_dict()
                    found = True
                    break
            if not found:
                transactions.append(transaction.to_dict())
            self._save_file("transactions", transactions)

    def save_transactions(self, transactions: List[Transaction]) -> None:
        """Save multiple transactions (batch operation)."""
        with self._get_lock("transactions"):
            existing = self._load_file("transactions")
            existing_ids = {t.get("tran_id") for t in existing}
            for transaction in transactions:
                if transaction.tran_id not in existing_ids:
                    existing.append(transaction.to_dict())
            self._save_file("transactions", existing)

    # User operations
    def get_users(self) -> List[User]:
        """Get all users."""
        with self._get_lock("users"):
            data = self._load_file("users")
            return [User.from_dict(d) for d in data]

    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        user_id = str(user_id).upper().ljust(8)[:8]
        users = self.get_users()
        for user in users:
            if user.user_id == user_id:
                return user
        return None

    def save_user(self, user: User) -> None:
        """Save or update a user."""
        with self._get_lock("users"):
            users = self._load_file("users")
            found = False
            for i, u in enumerate(users):
                if u.get("user_id") == user.user_id:
                    users[i] = user.to_dict(include_password=True)
                    found = True
                    break
            if not found:
                users.append(user.to_dict(include_password=True))
            self._save_file("users", users)

    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        user_id = str(user_id).upper().ljust(8)[:8]
        with self._get_lock("users"):
            users = self._load_file("users")
            new_users = [u for u in users if u.get("user_id") != user_id]
            if len(new_users) < len(users):
                self._save_file("users", new_users)
                return True
            return False

    # Card cross-reference operations
    def get_card_xrefs(self) -> List[CardXref]:
        """Get all card cross-references."""
        with self._get_lock("cardxref"):
            data = self._load_file("cardxref")
            return [CardXref.from_dict(d) for d in data]

    def get_card_xref(self, card_num: str) -> Optional[CardXref]:
        """Get card cross-reference by card number."""
        card_num = str(card_num).ljust(16)[:16]
        xrefs = self.get_card_xrefs()
        for xref in xrefs:
            if xref.card_num == card_num:
                return xref
        return None

    def get_xrefs_by_account(self, acct_id: str) -> List[CardXref]:
        """Get all card cross-references for an account."""
        acct_id = str(acct_id).zfill(11)[:11]
        xrefs = self.get_card_xrefs()
        return [xref for xref in xrefs if xref.acct_id == acct_id]

    def save_card_xref(self, xref: CardXref) -> None:
        """Save or update a card cross-reference."""
        with self._get_lock("cardxref"):
            xrefs = self._load_file("cardxref")
            found = False
            for i, x in enumerate(xrefs):
                if x.get("card_num") == xref.card_num:
                    xrefs[i] = xref.to_dict()
                    found = True
                    break
            if not found:
                xrefs.append(xref.to_dict())
            self._save_file("cardxref", xrefs)

    # Transaction type/category reference data
    def get_transaction_types(self) -> List[TransactionType]:
        """Get all transaction types."""
        with self._get_lock("trantypes"):
            data = self._load_file("trantypes")
            return [TransactionType.from_dict(d) for d in data]

    def get_transaction_categories(self) -> List[TransactionCategory]:
        """Get all transaction categories."""
        with self._get_lock("trancats"):
            data = self._load_file("trancats")
            return [TransactionCategory.from_dict(d) for d in data]


# Global data store instance
_data_store: Optional[DataStore] = None


def get_data_store(data_dir: Optional[str] = None) -> DataStore:
    """Get the global data store instance."""
    global _data_store
    if _data_store is None:
        _data_store = DataStore(data_dir)
    return _data_store
