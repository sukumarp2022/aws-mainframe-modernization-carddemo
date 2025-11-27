"""
Statement generation batch processor.

This module implements the batch statement generation functionality,
replacing the COBOL CBSTM03A batch program.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional

from ..models.transaction import Transaction
from ..models.account import Account
from ..services.data_store import get_data_store

logger = logging.getLogger(__name__)


@dataclass
class StatementTransaction:
    """Transaction line item for statement."""

    date: str
    description: str
    amount: Decimal
    type: str  # 'debit' or 'credit'


@dataclass
class Statement:
    """Account statement."""

    acct_id: str
    statement_date: date
    statement_period_start: date
    statement_period_end: date
    customer_name: str
    customer_address: str
    previous_balance: Decimal
    payments: Decimal
    purchases: Decimal
    interest_charges: Decimal
    fees: Decimal
    new_balance: Decimal
    minimum_payment: Decimal
    payment_due_date: date
    credit_limit: Decimal
    available_credit: Decimal
    transactions: List[StatementTransaction] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "acct_id": self.acct_id,
            "statement_date": self.statement_date.isoformat(),
            "statement_period_start": self.statement_period_start.isoformat(),
            "statement_period_end": self.statement_period_end.isoformat(),
            "customer_name": self.customer_name,
            "customer_address": self.customer_address,
            "previous_balance": str(self.previous_balance),
            "payments": str(self.payments),
            "purchases": str(self.purchases),
            "interest_charges": str(self.interest_charges),
            "fees": str(self.fees),
            "new_balance": str(self.new_balance),
            "minimum_payment": str(self.minimum_payment),
            "payment_due_date": self.payment_due_date.isoformat(),
            "credit_limit": str(self.credit_limit),
            "available_credit": str(self.available_credit),
            "transactions": [
                {
                    "date": t.date,
                    "description": t.description,
                    "amount": str(t.amount),
                    "type": t.type,
                }
                for t in self.transactions
            ],
        }

    def to_text(self) -> str:
        """Generate text format statement."""
        lines = []
        lines.append("=" * 60)
        lines.append("CREDIT CARD STATEMENT")
        lines.append("=" * 60)
        lines.append(f"Account Number: ***{self.acct_id[-4:]}")
        lines.append(f"Statement Date: {self.statement_date.strftime('%m/%d/%Y')}")
        lines.append(
            f"Statement Period: {self.statement_period_start.strftime('%m/%d/%Y')} - "
            f"{self.statement_period_end.strftime('%m/%d/%Y')}"
        )
        lines.append("")
        lines.append(f"{self.customer_name}")
        lines.append(self.customer_address)
        lines.append("")
        lines.append("-" * 60)
        lines.append("ACCOUNT SUMMARY")
        lines.append("-" * 60)
        lines.append(f"Previous Balance:          ${self.previous_balance:>12,.2f}")
        lines.append(f"Payments/Credits:          ${self.payments:>12,.2f}")
        lines.append(f"Purchases/Debits:          ${self.purchases:>12,.2f}")
        lines.append(f"Interest Charges:          ${self.interest_charges:>12,.2f}")
        lines.append(f"Fees:                      ${self.fees:>12,.2f}")
        lines.append("-" * 60)
        lines.append(f"New Balance:               ${self.new_balance:>12,.2f}")
        lines.append("")
        lines.append(f"Minimum Payment Due:       ${self.minimum_payment:>12,.2f}")
        lines.append(f"Payment Due Date:          {self.payment_due_date.strftime('%m/%d/%Y')}")
        lines.append("")
        lines.append(f"Credit Limit:              ${self.credit_limit:>12,.2f}")
        lines.append(f"Available Credit:          ${self.available_credit:>12,.2f}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("TRANSACTION DETAILS")
        lines.append("-" * 60)
        lines.append(f"{'Date':<12} {'Description':<30} {'Amount':>12}")
        lines.append("-" * 60)

        for tran in self.transactions:
            sign = "-" if tran.type == "credit" else ""
            lines.append(f"{tran.date:<12} {tran.description[:30]:<30} {sign}${abs(tran.amount):>10,.2f}")

        lines.append("=" * 60)
        lines.append("")
        return "\n".join(lines)


@dataclass
class StatementBatchResult:
    """Result of statement generation batch run."""

    statements_generated: int
    statements: List[Statement]
    start_time: datetime
    end_time: datetime

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "statements_generated": self.statements_generated,
            "statements": [s.to_dict() for s in self.statements],
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": self.duration_seconds,
        }


class StatementGenerationBatch:
    """
    Statement generation batch processor.

    Implements the logic from COBOL CBSTM03A program:
    - Generate monthly statements for all active accounts
    - Include transaction details
    - Calculate minimum payments
    """

    # Minimum payment percentage
    MIN_PAYMENT_PERCENTAGE = Decimal("0.02")  # 2% of balance
    MIN_PAYMENT_FLOOR = Decimal("25.00")  # Minimum $25

    def __init__(self):
        """Initialize the batch processor."""
        self._data_store = get_data_store()

    def generate_statements(
        self,
        statement_date: Optional[date] = None,
        period_days: int = 30,
    ) -> StatementBatchResult:
        """
        Generate statements for all active accounts.

        Args:
            statement_date: Statement date (defaults to today)
            period_days: Statement period in days

        Returns:
            StatementBatchResult with generated statements
        """
        if statement_date is None:
            statement_date = date.today()

        period_end = statement_date
        period_start = statement_date - timedelta(days=period_days)

        start_time = datetime.now()
        statements: List[Statement] = []

        logger.info("START OF EXECUTION OF STATEMENT GENERATION")

        # Get all active accounts
        accounts = self._data_store.get_accounts()

        for account in accounts:
            if not account.is_active:
                continue

            statement = self._generate_account_statement(
                account, statement_date, period_start, period_end
            )
            if statement:
                statements.append(statement)

        end_time = datetime.now()

        result = StatementBatchResult(
            statements_generated=len(statements),
            statements=statements,
            start_time=start_time,
            end_time=end_time,
        )

        logger.info(f"STATEMENTS GENERATED: {result.statements_generated}")
        logger.info("END OF EXECUTION OF STATEMENT GENERATION")

        return result

    def _generate_account_statement(
        self,
        account: Account,
        statement_date: date,
        period_start: date,
        period_end: date,
    ) -> Optional[Statement]:
        """
        Generate statement for a single account.

        Args:
            account: Account to generate statement for
            statement_date: Statement date
            period_start: Period start date
            period_end: Period end date

        Returns:
            Generated Statement or None
        """
        # Get customer info
        xrefs = self._data_store.get_xrefs_by_account(account.acct_id)
        customer = None
        if xrefs:
            customer = self._data_store.get_customer(xrefs[0].cust_id)

        customer_name = customer.full_name if customer else "Account Holder"
        customer_address = customer.full_address if customer else ""

        # Get transactions for the period
        cards = self._data_store.get_cards_by_account(account.acct_id)
        all_transactions: List[Transaction] = []
        for card in cards:
            card_transactions = self._data_store.get_transactions(card.card_num)
            for tran in card_transactions:
                if tran.orig_ts:
                    tran_date = tran.orig_ts.date()
                    if period_start <= tran_date <= period_end:
                        all_transactions.append(tran)

        # Sort transactions by date
        all_transactions.sort(key=lambda t: t.orig_ts or datetime.min)

        # Calculate statement amounts
        payments = Decimal("0.00")
        purchases = Decimal("0.00")
        interest_charges = Decimal("0.00")
        fees = Decimal("0.00")

        statement_transactions: List[StatementTransaction] = []

        for tran in all_transactions:
            tran_date = tran.orig_ts.strftime("%m/%d/%Y") if tran.orig_ts else ""

            if tran.amount < 0:
                # Payment/Credit
                payments += abs(tran.amount)
                statement_transactions.append(
                    StatementTransaction(
                        date=tran_date,
                        description=tran.description or "Payment",
                        amount=abs(tran.amount),
                        type="credit",
                    )
                )
            else:
                # Purchase/Debit
                if tran.cat_cd == "0005":
                    # Interest charge
                    interest_charges += tran.amount
                elif tran.cat_cd == "0006":
                    # Fee
                    fees += tran.amount
                else:
                    purchases += tran.amount

                statement_transactions.append(
                    StatementTransaction(
                        date=tran_date,
                        description=tran.description or tran.merchant_name or "Purchase",
                        amount=tran.amount,
                        type="debit",
                    )
                )

        # Calculate balances
        previous_balance = account.curr_bal - purchases + payments - interest_charges - fees
        new_balance = account.curr_bal

        # Calculate minimum payment
        min_payment = max(
            new_balance * self.MIN_PAYMENT_PERCENTAGE,
            self.MIN_PAYMENT_FLOOR,
        )
        if min_payment > new_balance:
            min_payment = new_balance
        if min_payment < 0:
            min_payment = Decimal("0.00")

        # Payment due date (25 days after statement date)
        payment_due_date = statement_date + timedelta(days=25)

        return Statement(
            acct_id=account.acct_id,
            statement_date=statement_date,
            statement_period_start=period_start,
            statement_period_end=period_end,
            customer_name=customer_name,
            customer_address=customer_address,
            previous_balance=previous_balance,
            payments=payments,
            purchases=purchases,
            interest_charges=interest_charges,
            fees=fees,
            new_balance=new_balance,
            minimum_payment=min_payment.quantize(Decimal("0.01")),
            payment_due_date=payment_due_date,
            credit_limit=account.credit_limit,
            available_credit=account.available_credit,
            transactions=statement_transactions,
        )


def run_statement_generation(
    statement_date: Optional[date] = None,
    period_days: int = 30,
) -> StatementBatchResult:
    """
    Run the statement generation batch job.

    This is the entry point that replaces the CREASTMT JCL job.

    Args:
        statement_date: Statement date (defaults to today)
        period_days: Statement period in days

    Returns:
        StatementBatchResult with generated statements
    """
    processor = StatementGenerationBatch()
    return processor.generate_statements(statement_date, period_days)
