"""
Interest calculation batch processor.

This module implements the batch interest calculation functionality,
replacing the COBOL CBACT04C batch program.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from ..models.transaction import Transaction
from ..models.account import Account
from ..services.data_store import get_data_store

logger = logging.getLogger(__name__)


@dataclass
class InterestResult:
    """Result of interest calculation for an account."""

    acct_id: str
    balance: Decimal
    interest_rate: Decimal
    monthly_interest: Decimal
    transaction_id: str


@dataclass
class InterestBatchResult:
    """Result of interest calculation batch run."""

    accounts_processed: int
    total_interest: Decimal
    interest_transactions: List[InterestResult]
    start_time: datetime
    end_time: datetime

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "accounts_processed": self.accounts_processed,
            "total_interest": str(self.total_interest),
            "interest_transactions": [
                {
                    "acct_id": r.acct_id,
                    "balance": str(r.balance),
                    "interest_rate": str(r.interest_rate),
                    "monthly_interest": str(r.monthly_interest),
                    "transaction_id": r.transaction_id,
                }
                for r in self.interest_transactions
            ],
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": self.duration_seconds,
        }


class InterestCalculationBatch:
    """
    Interest calculation batch processor.

    Implements the logic from COBOL CBACT04C program:
    - Read transaction category balance file
    - Look up disclosure group for interest rate
    - Compute monthly interest
    - Update account balance
    - Create interest transaction record
    """

    # Default annual interest rate (percentage)
    DEFAULT_INTEREST_RATE = Decimal("18.99")

    def __init__(self):
        """Initialize the batch processor."""
        self._data_store = get_data_store()
        self._transaction_counter = 0

    def calculate_interest(
        self,
        process_date: Optional[date] = None,
    ) -> InterestBatchResult:
        """
        Calculate interest for all accounts.

        Args:
            process_date: Date for interest calculation (defaults to today)

        Returns:
            InterestBatchResult with calculation statistics
        """
        if process_date is None:
            process_date = date.today()

        start_time = datetime.now()
        interest_results: List[InterestResult] = []
        total_interest = Decimal("0.00")

        logger.info("START OF EXECUTION OF PROGRAM INTEREST CALCULATION")

        # Get all accounts
        accounts = self._data_store.get_accounts()

        for account in accounts:
            if not account.is_active:
                continue

            # Only charge interest on positive balances
            if account.curr_bal <= 0:
                continue

            # Get interest rate (in production, this would come from disclosure group)
            interest_rate = self._get_interest_rate(account)

            # Compute monthly interest: (balance * annual_rate) / 12 / 100
            monthly_interest = (
                (account.curr_bal * interest_rate) / Decimal("1200")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            if monthly_interest > 0:
                # Create interest transaction
                transaction = self._create_interest_transaction(
                    account, monthly_interest, process_date
                )

                # Update account balance
                account.curr_bal += monthly_interest
                account.curr_cyc_credit = Decimal("0.00")
                account.curr_cyc_debit = Decimal("0.00")
                self._data_store.save_account(account)

                # Record result
                result = InterestResult(
                    acct_id=account.acct_id,
                    balance=account.curr_bal,
                    interest_rate=interest_rate,
                    monthly_interest=monthly_interest,
                    transaction_id=transaction.tran_id,
                )
                interest_results.append(result)
                total_interest += monthly_interest

                logger.debug(f"Account {account.acct_id}: Interest ${monthly_interest}")

        end_time = datetime.now()

        result = InterestBatchResult(
            accounts_processed=len(interest_results),
            total_interest=total_interest,
            interest_transactions=interest_results,
            start_time=start_time,
            end_time=end_time,
        )

        logger.info(f"ACCOUNTS PROCESSED: {result.accounts_processed}")
        logger.info(f"TOTAL INTEREST CHARGED: ${result.total_interest}")
        logger.info("END OF EXECUTION OF PROGRAM INTEREST CALCULATION")

        return result

    def _get_interest_rate(self, account: Account) -> Decimal:
        """
        Get interest rate for account.

        In the original COBOL program, this looks up the disclosure group.
        For simplicity, we use a default rate or group-based rate.

        Args:
            account: Account to get rate for

        Returns:
            Annual interest rate as percentage
        """
        # Simple implementation: use default rate
        # In production, this would look up rates from a disclosure group table
        return self.DEFAULT_INTEREST_RATE

    def _create_interest_transaction(
        self,
        account: Account,
        amount: Decimal,
        process_date: date,
    ) -> Transaction:
        """
        Create an interest charge transaction.

        Args:
            account: Account to charge
            amount: Interest amount
            process_date: Processing date

        Returns:
            Created Transaction
        """
        self._transaction_counter += 1

        # Generate transaction ID (matching COBOL format)
        tran_id = f"{process_date.strftime('%Y%m%d')}{self._transaction_counter:06d}"

        # Get a card for the account
        cards = self._data_store.get_cards_by_account(account.acct_id)
        card_num = cards[0].card_num if cards else ""

        now = datetime.now()
        transaction = Transaction(
            tran_id=tran_id,
            type_cd="01",  # Interest type
            cat_cd="0005",  # Interest category
            source="System",
            description=f"Int. for a/c {account.acct_id}",
            amount=amount,
            merchant_id="",
            merchant_name="",
            merchant_city="",
            merchant_zip="",
            card_num=card_num,
            orig_ts=now,
            proc_ts=now,
        )

        self._data_store.save_transaction(transaction)
        return transaction


def run_interest_calculation(
    process_date: Optional[date] = None,
) -> InterestBatchResult:
    """
    Run the interest calculation batch job.

    This is the entry point that replaces the INTCALC JCL job.

    Args:
        process_date: Date for interest calculation (defaults to today)

    Returns:
        InterestBatchResult with calculation statistics
    """
    processor = InterestCalculationBatch()
    return processor.calculate_interest(process_date)
