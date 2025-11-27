"""
Account service for CardDemo.

This module provides account management functionality,
replacing the COBOL account view/update programs (COACTVWC, COACTUPC).
"""

from decimal import Decimal
from typing import List, Optional, Tuple

from ..models.account import Account
from ..models.card import Card
from ..models.customer import Customer
from .data_store import get_data_store


class AccountService:
    """
    Account management service.

    Provides account CRUD operations and related functionality.
    Replaces COBOL programs COACTVWC (view) and COACTUPC (update).
    """

    def __init__(self):
        """Initialize the account service."""
        self._data_store = get_data_store()

    def list_accounts(
        self,
        page: int = 1,
        page_size: int = 10,
        active_only: bool = False,
    ) -> Tuple[List[Account], int]:
        """
        List accounts with pagination.

        Args:
            page: Page number (1-based)
            page_size: Number of records per page
            active_only: If True, only return active accounts

        Returns:
            Tuple of (accounts, total_count)
        """
        accounts = self._data_store.get_accounts()

        if active_only:
            accounts = [a for a in accounts if a.is_active]

        total = len(accounts)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        accounts = accounts[start:end]

        return accounts, total

    def get_account(self, acct_id: str) -> Optional[Account]:
        """
        Get account by ID.

        Args:
            acct_id: Account ID

        Returns:
            Account if found, None otherwise
        """
        return self._data_store.get_account(acct_id)

    def get_account_details(self, acct_id: str) -> Optional[dict]:
        """
        Get full account details including cards and customer info.

        Args:
            acct_id: Account ID

        Returns:
            Dictionary with account, cards, and customer info
        """
        account = self._data_store.get_account(acct_id)
        if account is None:
            return None

        # Get associated cards
        cards = self._data_store.get_cards_by_account(acct_id)

        # Get associated customer via cross-reference
        xrefs = self._data_store.get_xrefs_by_account(acct_id)
        customers = []
        for xref in xrefs:
            customer = self._data_store.get_customer(xref.cust_id)
            if customer:
                customers.append(customer)

        return {
            "account": account.to_dict(),
            "cards": [card.to_dict() for card in cards],
            "customers": [cust.to_dict() for cust in customers],
        }

    def update_account(
        self,
        acct_id: str,
        active_status: Optional[str] = None,
        credit_limit: Optional[Decimal] = None,
        cash_credit_limit: Optional[Decimal] = None,
        group_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Update account details.

        Args:
            acct_id: Account ID
            active_status: New active status (Y/N)
            credit_limit: New credit limit
            cash_credit_limit: New cash credit limit
            group_id: New group ID

        Returns:
            Tuple of (success, message)
        """
        account = self._data_store.get_account(acct_id)
        if account is None:
            return False, "Account not found"

        # Update fields if provided
        if active_status is not None:
            if active_status not in ("Y", "N"):
                return False, "Invalid active status. Use Y or N"
            account.active_status = active_status

        if credit_limit is not None:
            if credit_limit < 0:
                return False, "Credit limit cannot be negative"
            account.credit_limit = credit_limit

        if cash_credit_limit is not None:
            if cash_credit_limit < 0:
                return False, "Cash credit limit cannot be negative"
            account.cash_credit_limit = cash_credit_limit

        if group_id is not None:
            account.group_id = group_id[:10]

        self._data_store.save_account(account)
        return True, "Account updated successfully"

    def get_account_balance(self, acct_id: str) -> Optional[dict]:
        """
        Get account balance summary.

        Args:
            acct_id: Account ID

        Returns:
            Dictionary with balance information
        """
        account = self._data_store.get_account(acct_id)
        if account is None:
            return None

        return {
            "acct_id": account.acct_id,
            "curr_bal": str(account.curr_bal),
            "credit_limit": str(account.credit_limit),
            "available_credit": str(account.available_credit),
            "curr_cyc_credit": str(account.curr_cyc_credit),
            "curr_cyc_debit": str(account.curr_cyc_debit),
            "is_overlimit": account.is_overlimit,
        }


class CardService:
    """
    Card management service.

    Provides card CRUD operations.
    Replaces COBOL programs COCRDLIC (list), COCRDSLC (view), COCRDUPC (update).
    """

    def __init__(self):
        """Initialize the card service."""
        self._data_store = get_data_store()

    def list_cards(
        self,
        acct_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Card], int]:
        """
        List cards with optional account filter and pagination.

        Args:
            acct_id: Optional account ID filter
            page: Page number (1-based)
            page_size: Number of records per page

        Returns:
            Tuple of (cards, total_count)
        """
        if acct_id:
            cards = self._data_store.get_cards_by_account(acct_id)
        else:
            cards = self._data_store.get_cards()

        total = len(cards)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        cards = cards[start:end]

        return cards, total

    def get_card(self, card_num: str) -> Optional[Card]:
        """
        Get card by number.

        Args:
            card_num: Card number

        Returns:
            Card if found, None otherwise
        """
        return self._data_store.get_card(card_num)

    def get_card_details(self, card_num: str) -> Optional[dict]:
        """
        Get full card details including account and customer info.

        Args:
            card_num: Card number

        Returns:
            Dictionary with card, account, and customer info
        """
        card = self._data_store.get_card(card_num)
        if card is None:
            return None

        # Get associated account
        account = self._data_store.get_account(card.acct_id)

        # Get associated customer via cross-reference
        xref = self._data_store.get_card_xref(card_num)
        customer = None
        if xref:
            customer = self._data_store.get_customer(xref.cust_id)

        return {
            "card": card.to_dict(),
            "account": account.to_dict() if account else None,
            "customer": customer.to_dict() if customer else None,
        }

    def update_card(
        self,
        card_num: str,
        active_status: Optional[str] = None,
        embossed_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Update card details.

        Args:
            card_num: Card number
            active_status: New active status (Y/N)
            embossed_name: New embossed name

        Returns:
            Tuple of (success, message)
        """
        card = self._data_store.get_card(card_num)
        if card is None:
            return False, "Card not found"

        if active_status is not None:
            if active_status not in ("Y", "N"):
                return False, "Invalid active status. Use Y or N"
            card.active_status = active_status

        if embossed_name is not None:
            card.embossed_name = embossed_name[:50]

        self._data_store.save_card(card)
        return True, "Card updated successfully"


class CustomerService:
    """
    Customer management service.

    Provides customer CRUD operations.
    """

    def __init__(self):
        """Initialize the customer service."""
        self._data_store = get_data_store()

    def list_customers(
        self,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Customer], int]:
        """
        List customers with pagination.

        Args:
            page: Page number (1-based)
            page_size: Number of records per page

        Returns:
            Tuple of (customers, total_count)
        """
        customers = self._data_store.get_customers()
        total = len(customers)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        customers = customers[start:end]

        return customers, total

    def get_customer(self, cust_id: str) -> Optional[Customer]:
        """
        Get customer by ID.

        Args:
            cust_id: Customer ID

        Returns:
            Customer if found, None otherwise
        """
        return self._data_store.get_customer(cust_id)

    def update_customer(
        self,
        cust_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_num_1: Optional[str] = None,
        phone_num_2: Optional[str] = None,
        addr_line_1: Optional[str] = None,
        addr_line_2: Optional[str] = None,
        addr_line_3: Optional[str] = None,
        addr_state_cd: Optional[str] = None,
        addr_zip: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Update customer details.

        Args:
            cust_id: Customer ID
            Various optional fields to update

        Returns:
            Tuple of (success, message)
        """
        customer = self._data_store.get_customer(cust_id)
        if customer is None:
            return False, "Customer not found"

        if first_name is not None:
            customer.first_name = first_name[:25]
        if last_name is not None:
            customer.last_name = last_name[:25]
        if phone_num_1 is not None:
            customer.phone_num_1 = phone_num_1[:15]
        if phone_num_2 is not None:
            customer.phone_num_2 = phone_num_2[:15]
        if addr_line_1 is not None:
            customer.addr_line_1 = addr_line_1[:50]
        if addr_line_2 is not None:
            customer.addr_line_2 = addr_line_2[:50]
        if addr_line_3 is not None:
            customer.addr_line_3 = addr_line_3[:50]
        if addr_state_cd is not None:
            customer.addr_state_cd = addr_state_cd[:2].upper()
        if addr_zip is not None:
            customer.addr_zip = addr_zip[:10]

        self._data_store.save_customer(customer)
        return True, "Customer updated successfully"


# Service instances
_account_service: Optional[AccountService] = None
_card_service: Optional[CardService] = None
_customer_service: Optional[CustomerService] = None


def get_account_service() -> AccountService:
    """Get the global account service instance."""
    global _account_service
    if _account_service is None:
        _account_service = AccountService()
    return _account_service


def get_card_service() -> CardService:
    """Get the global card service instance."""
    global _card_service
    if _card_service is None:
        _card_service = CardService()
    return _card_service


def get_customer_service() -> CustomerService:
    """Get the global customer service instance."""
    global _customer_service
    if _customer_service is None:
        _customer_service = CustomerService()
    return _customer_service
