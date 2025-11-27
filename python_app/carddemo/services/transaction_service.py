"""
Transaction service for CardDemo.

This module provides transaction management functionality,
replacing the COBOL transaction programs (COTRN00C, COTRN01C, COTRN02C, etc.).
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from ..models.transaction import Transaction, TransactionType, TransactionCategory
from .data_store import get_data_store


class TransactionService:
    """
    Transaction management service.

    Provides transaction CRUD operations and reporting.
    Replaces COBOL programs:
    - COTRN00C: Transaction list
    - COTRN01C: Transaction view
    - COTRN02C: Transaction add
    - CORPT00C: Transaction reports
    """

    def __init__(self):
        """Initialize the transaction service."""
        self._data_store = get_data_store()

    def list_transactions(
        self,
        card_num: Optional[str] = None,
        acct_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Transaction], int]:
        """
        List transactions with filtering and pagination.

        Args:
            card_num: Optional card number filter
            acct_id: Optional account ID filter (will get all cards for account)
            start_date: Optional start date filter
            end_date: Optional end date filter
            page: Page number (1-based)
            page_size: Number of records per page

        Returns:
            Tuple of (transactions, total_count)
        """
        # Get transactions
        if card_num:
            transactions = self._data_store.get_transactions(card_num)
        elif acct_id:
            # Get all cards for account and their transactions
            cards = self._data_store.get_cards_by_account(acct_id)
            transactions = []
            for card in cards:
                transactions.extend(self._data_store.get_transactions(card.card_num))
        else:
            transactions = self._data_store.get_transactions()

        # Apply date filters
        if start_date:
            transactions = [
                t for t in transactions if t.orig_ts and t.orig_ts >= start_date
            ]
        if end_date:
            transactions = [
                t for t in transactions if t.orig_ts and t.orig_ts <= end_date
            ]

        # Sort by date descending (most recent first)
        transactions.sort(key=lambda t: t.orig_ts or datetime.min, reverse=True)

        total = len(transactions)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        transactions = transactions[start:end]

        return transactions, total

    def get_transaction(self, tran_id: str) -> Optional[Transaction]:
        """
        Get transaction by ID.

        Args:
            tran_id: Transaction ID

        Returns:
            Transaction if found, None otherwise
        """
        return self._data_store.get_transaction(tran_id)

    def add_transaction(
        self,
        card_num: str,
        amount: Decimal,
        type_cd: str = "01",
        cat_cd: str = "0000",
        description: str = "",
        merchant_name: str = "",
        merchant_city: str = "",
        merchant_zip: str = "",
        source: str = "Online",
    ) -> Tuple[bool, Optional[Transaction], str]:
        """
        Add a new transaction.

        Implements the logic from COBOL COTRN02C program:
        - Validates card exists and is active
        - Validates account has sufficient credit
        - Creates transaction record
        - Updates account balances

        Args:
            card_num: Card number
            amount: Transaction amount (positive for purchases, negative for credits)
            type_cd: Transaction type code
            cat_cd: Transaction category code
            description: Transaction description
            merchant_name: Merchant name
            merchant_city: Merchant city
            merchant_zip: Merchant ZIP code
            source: Transaction source

        Returns:
            Tuple of (success, transaction, message)
        """
        # Validate card
        card = self._data_store.get_card(card_num)
        if card is None:
            return False, None, "Invalid card number"

        if not card.is_active:
            return False, None, "Card is not active"

        if card.is_expired:
            return False, None, "Card has expired"

        # Validate account
        account = self._data_store.get_account(card.acct_id)
        if account is None:
            return False, None, "Account not found"

        if not account.is_active:
            return False, None, "Account is not active"

        # Check credit limit for purchases (positive amounts)
        if amount > 0:
            new_balance = account.curr_bal + amount
            if new_balance > account.credit_limit:
                return False, None, "Transaction would exceed credit limit"

        # Generate transaction ID
        tran_id = self._generate_transaction_id()

        # Create transaction
        now = datetime.now()
        transaction = Transaction(
            tran_id=tran_id,
            type_cd=type_cd,
            cat_cd=cat_cd,
            source=source,
            description=description,
            amount=amount,
            merchant_name=merchant_name,
            merchant_city=merchant_city,
            merchant_zip=merchant_zip,
            card_num=card_num,
            orig_ts=now,
            proc_ts=now,
        )

        # Update account balance
        account.curr_bal += amount
        if amount >= 0:
            account.curr_cyc_debit += amount
        else:
            account.curr_cyc_credit += abs(amount)

        # Save
        self._data_store.save_transaction(transaction)
        self._data_store.save_account(account)

        return True, transaction, "Transaction processed successfully"

    def _generate_transaction_id(self) -> str:
        """Generate a unique transaction ID."""
        now = datetime.now()
        # Format: YYYYMMDDHHMMSS + 2-digit sequence
        base = now.strftime("%Y%m%d%H%M%S")

        # Find next available sequence number
        existing = self._data_store.get_transactions()
        existing_ids = {t.tran_id for t in existing}

        for seq in range(100):
            tran_id = f"{base}{seq:02d}"
            if tran_id not in existing_ids:
                return tran_id

        # Fallback: use microseconds
        return now.strftime("%Y%m%d%H%M%S") + str(now.microsecond)[:2]

    def get_transaction_summary(
        self,
        acct_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """
        Get transaction summary for an account.

        Args:
            acct_id: Account ID
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Dictionary with summary statistics
        """
        transactions, _ = self.list_transactions(
            acct_id=acct_id,
            start_date=start_date,
            end_date=end_date,
            page=1,
            page_size=10000,  # Get all transactions
        )

        total_debits = Decimal("0.00")
        total_credits = Decimal("0.00")

        for tran in transactions:
            if tran.amount >= 0:
                total_debits += tran.amount
            else:
                total_credits += abs(tran.amount)

        return {
            "acct_id": acct_id,
            "transaction_count": len(transactions),
            "total_debits": str(total_debits),
            "total_credits": str(total_credits),
            "net_amount": str(total_debits - total_credits),
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        }

    def get_transaction_types(self) -> List[TransactionType]:
        """Get all transaction types."""
        return self._data_store.get_transaction_types()

    def get_transaction_categories(self) -> List[TransactionCategory]:
        """Get all transaction categories."""
        return self._data_store.get_transaction_categories()


class BillPaymentService:
    """
    Bill payment service.

    Provides bill payment functionality.
    Replaces COBOL program COBIL00C.
    """

    def __init__(self):
        """Initialize the bill payment service."""
        self._data_store = get_data_store()
        self._transaction_service = TransactionService()

    def make_payment(
        self,
        acct_id: str,
        amount: Decimal,
        source: str = "Online Payment",
    ) -> Tuple[bool, Optional[Transaction], str]:
        """
        Make a bill payment.

        Args:
            acct_id: Account ID
            amount: Payment amount (must be positive)
            source: Payment source description

        Returns:
            Tuple of (success, transaction, message)
        """
        if amount <= 0:
            return False, None, "Payment amount must be positive"

        # Get account
        account = self._data_store.get_account(acct_id)
        if account is None:
            return False, None, "Account not found"

        # Get a card for the account (to record the transaction)
        cards = self._data_store.get_cards_by_account(acct_id)
        if not cards:
            return False, None, "No cards found for account"

        card = cards[0]  # Use first card

        # Create payment transaction (negative amount = credit)
        return self._transaction_service.add_transaction(
            card_num=card.card_num,
            amount=-amount,  # Negative amount for payment
            type_cd="02",  # Payment type
            cat_cd="0001",  # Payment category
            description=f"Payment - {source}",
            source=source,
        )


# Service instances
_transaction_service: Optional[TransactionService] = None
_bill_payment_service: Optional[BillPaymentService] = None


def get_transaction_service() -> TransactionService:
    """Get the global transaction service instance."""
    global _transaction_service
    if _transaction_service is None:
        _transaction_service = TransactionService()
    return _transaction_service


def get_bill_payment_service() -> BillPaymentService:
    """Get the global bill payment service instance."""
    global _bill_payment_service
    if _bill_payment_service is None:
        _bill_payment_service = BillPaymentService()
    return _bill_payment_service
