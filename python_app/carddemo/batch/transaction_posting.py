"""
Transaction posting batch processor.

This module implements the batch transaction posting functionality,
replacing the COBOL CBTRN02C batch program.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from ..models.transaction import Transaction
from ..services.data_store import get_data_store

logger = logging.getLogger(__name__)


@dataclass
class PostingResult:
    """Result of posting a transaction."""

    tran_id: str
    success: bool
    reason: str = ""
    reason_code: int = 0


@dataclass
class PostingBatchResult:
    """Result of a batch posting run."""

    transactions_processed: int
    transactions_posted: int
    transactions_rejected: int
    rejected_transactions: List[PostingResult]
    start_time: datetime
    end_time: datetime

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "transactions_processed": self.transactions_processed,
            "transactions_posted": self.transactions_posted,
            "transactions_rejected": self.transactions_rejected,
            "rejected_transactions": [
                {"tran_id": r.tran_id, "reason": r.reason, "reason_code": r.reason_code}
                for r in self.rejected_transactions
            ],
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": self.duration_seconds,
        }


class TransactionPostingBatch:
    """
    Transaction posting batch processor.

    Implements the logic from COBOL CBTRN02C program:
    - Read daily transaction file
    - Validate each transaction
    - Post valid transactions to transaction master
    - Write rejected transactions to reject file
    - Update account balances
    """

    # Validation reason codes (matching COBOL program)
    REASON_INVALID_CARD = 100
    REASON_ACCOUNT_NOT_FOUND = 101
    REASON_OVERLIMIT = 102
    REASON_EXPIRED_ACCOUNT = 103

    def __init__(self):
        """Initialize the batch processor."""
        self._data_store = get_data_store()

    def process_daily_transactions(
        self,
        transactions: List[Transaction],
    ) -> PostingBatchResult:
        """
        Process a batch of daily transactions.

        Args:
            transactions: List of transactions to process

        Returns:
            PostingBatchResult with processing statistics
        """
        start_time = datetime.now()
        rejected: List[PostingResult] = []
        posted_count = 0

        logger.info("START OF EXECUTION OF TRANSACTION POSTING")
        logger.info("Processing %d transactions", len(transactions))

        for transaction in transactions:
            # Validate transaction
            success, reason_code, reason_desc = self._validate_transaction(transaction)

            if success:
                # Post the transaction
                self._post_transaction(transaction)
                posted_count += 1
            else:
                # Record rejection
                rejected.append(
                    PostingResult(
                        tran_id=transaction.tran_id,
                        success=False,
                        reason=reason_desc,
                        reason_code=reason_code,
                    )
                )

        end_time = datetime.now()

        result = PostingBatchResult(
            transactions_processed=len(transactions),
            transactions_posted=posted_count,
            transactions_rejected=len(rejected),
            rejected_transactions=rejected,
            start_time=start_time,
            end_time=end_time,
        )

        logger.info("TRANSACTIONS PROCESSED: %d", result.transactions_processed)
        logger.info("TRANSACTIONS POSTED: %d", result.transactions_posted)
        logger.info("TRANSACTIONS REJECTED: %d", result.transactions_rejected)
        logger.info("END OF EXECUTION OF TRANSACTION POSTING")

        return result

    def _validate_transaction(
        self, transaction: Transaction
    ) -> Tuple[bool, int, str]:
        """
        Validate a transaction.

        Implements validation logic from COBOL 1500-VALIDATE-TRAN:
        - Look up card cross-reference
        - Look up account
        - Check credit limit
        - Check expiration date

        Returns:
            Tuple of (success, reason_code, reason_description)
        """
        # Look up card cross-reference
        xref = self._data_store.get_card_xref(transaction.card_num)
        if xref is None:
            return False, self.REASON_INVALID_CARD, "INVALID CARD NUMBER FOUND"

        # Look up account
        account = self._data_store.get_account(xref.acct_id)
        if account is None:
            return False, self.REASON_ACCOUNT_NOT_FOUND, "ACCOUNT RECORD NOT FOUND"

        # Check credit limit
        temp_balance = (
            account.curr_cyc_credit - account.curr_cyc_debit + transaction.amount
        )
        if account.credit_limit < temp_balance:
            return False, self.REASON_OVERLIMIT, "OVERLIMIT TRANSACTION"

        # Check account expiration
        if account.expiration_date:
            tran_date = transaction.orig_ts.date() if transaction.orig_ts else None
            if tran_date and account.expiration_date < tran_date:
                return (
                    False,
                    self.REASON_EXPIRED_ACCOUNT,
                    "TRANSACTION RECEIVED AFTER ACCT EXPIRATION",
                )

        return True, 0, ""

    def _post_transaction(self, transaction: Transaction) -> None:
        """
        Post a validated transaction.

        Implements logic from COBOL 2000-POST-TRANSACTION:
        - Update transaction category balance
        - Update account record
        - Write transaction to file
        """
        # Set processing timestamp
        transaction.proc_ts = datetime.now()

        # Update account balance
        xref = self._data_store.get_card_xref(transaction.card_num)
        if xref:
            account = self._data_store.get_account(xref.acct_id)
            if account:
                account.curr_bal += transaction.amount
                if transaction.amount >= 0:
                    account.curr_cyc_credit += transaction.amount
                else:
                    account.curr_cyc_debit += transaction.amount

                self._data_store.save_account(account)

        # Save transaction
        self._data_store.save_transaction(transaction)


def run_transaction_posting(input_file: Optional[str] = None) -> PostingBatchResult:
    """
    Run the transaction posting batch job.

    This is the entry point that replaces the POSTTRAN JCL job.

    Args:
        input_file: Optional path to daily transaction file (JSON format)

    Returns:
        PostingBatchResult with processing statistics
    """
    processor = TransactionPostingBatch()

    if input_file:
        # Load transactions from file
        import json

        with open(input_file, "r") as f:
            data = json.load(f)
        transactions = [Transaction.from_dict(d) for d in data]
    else:
        # Use transactions from data store marked for processing
        # In a real implementation, this would read from a staging area
        transactions = []

    return processor.process_daily_transactions(transactions)
