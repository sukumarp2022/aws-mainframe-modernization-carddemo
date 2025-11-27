"""Tests for data models."""

import pytest
from datetime import date
from decimal import Decimal

from carddemo.models.account import Account
from carddemo.models.card import Card
from carddemo.models.customer import Customer
from carddemo.models.transaction import Transaction
from carddemo.models.user import User, CardXref


class TestAccount:
    """Tests for Account model."""

    def test_create_account(self):
        """Test account creation."""
        account = Account(
            acct_id="1",
            active_status="Y",
            curr_bal=Decimal("1000.00"),
            credit_limit=Decimal("5000.00"),
        )

        assert account.acct_id == "00000000001"
        assert account.is_active is True
        assert account.available_credit == Decimal("4000.00")

    def test_account_overlimit(self):
        """Test overlimit detection."""
        account = Account(
            acct_id="1",
            curr_bal=Decimal("6000.00"),
            credit_limit=Decimal("5000.00"),
        )

        assert account.is_overlimit is True

    def test_account_to_dict(self):
        """Test account serialization."""
        account = Account(
            acct_id="1",
            curr_bal=Decimal("1000.00"),
            credit_limit=Decimal("5000.00"),
            open_date=date(2020, 1, 15),
        )

        data = account.to_dict()
        assert data["acct_id"] == "00000000001"
        assert data["curr_bal"] == "1000.00"
        assert data["open_date"] == "2020-01-15"

    def test_account_from_dict(self):
        """Test account deserialization."""
        data = {
            "acct_id": "12345",
            "curr_bal": "2500.50",
            "credit_limit": "10000.00",
            "open_date": "2021-06-01",
        }

        account = Account.from_dict(data)
        assert account.acct_id == "00000012345"
        assert account.curr_bal == Decimal("2500.50")
        assert account.open_date == date(2021, 6, 1)


class TestCard:
    """Tests for Card model."""

    def test_create_card(self):
        """Test card creation."""
        card = Card(
            card_num="1234567890123456",
            acct_id="1",
            cvv_cd="123",
            embossed_name="John Doe",
        )

        assert card.card_num == "1234567890123456"
        assert card.acct_id == "00000000001"
        assert card.cvv_cd == "123"

    def test_card_masked_number(self):
        """Test masked card number."""
        card = Card(card_num="1234567890123456", acct_id="1")
        assert card.masked_card_num == "************3456"

    def test_card_expired(self):
        """Test expiration check."""
        card = Card(
            card_num="1234567890123456",
            acct_id="1",
            expiration_date=date(2020, 1, 1),
        )
        assert card.is_expired is True

        card2 = Card(
            card_num="1234567890123456",
            acct_id="1",
            expiration_date=date(2030, 12, 31),
        )
        assert card2.is_expired is False


class TestCustomer:
    """Tests for Customer model."""

    def test_create_customer(self):
        """Test customer creation."""
        customer = Customer(
            cust_id="1",
            first_name="John",
            middle_name="Q",
            last_name="Public",
        )

        assert customer.cust_id == "000000001"
        assert customer.full_name == "John Q Public"

    def test_customer_masked_ssn(self):
        """Test masked SSN."""
        customer = Customer(cust_id="1", ssn="123456789")
        assert customer.masked_ssn == "***-**-6789"


class TestTransaction:
    """Tests for Transaction model."""

    def test_create_transaction(self):
        """Test transaction creation."""
        transaction = Transaction(
            tran_id="1234567890123456",
            amount=Decimal("99.99"),
            description="Test purchase",
        )

        assert transaction.tran_id == "1234567890123456"
        assert transaction.amount == Decimal("99.99")
        assert transaction.is_debit is True
        assert transaction.is_credit is False

    def test_transaction_credit(self):
        """Test credit transaction."""
        transaction = Transaction(
            tran_id="1",
            amount=Decimal("-50.00"),
        )

        assert transaction.is_credit is True
        assert transaction.is_debit is False


class TestUser:
    """Tests for User model."""

    def test_create_user(self):
        """Test user creation."""
        user = User(
            user_id="testuser",
            first_name="Test",
            last_name="User",
            password="secret",
            user_type="U",
        )

        assert user.user_id == "TESTUSER"
        assert user.is_admin is False
        assert user.full_name == "Test User"

    def test_admin_user(self):
        """Test admin user."""
        user = User(
            user_id="admin",
            user_type="A",
        )

        assert user.is_admin is True

    def test_verify_password(self):
        """Test password verification."""
        user = User(user_id="test", password="SECRET")

        assert user.verify_password("SECRET") is True
        assert user.verify_password("secret") is True  # Case insensitive
        assert user.verify_password("wrong") is False


class TestCardXref:
    """Tests for CardXref model."""

    def test_create_xref(self):
        """Test cross-reference creation."""
        xref = CardXref(
            card_num="1234567890123456",
            cust_id="1",
            acct_id="2",
        )

        assert xref.card_num == "1234567890123456"
        assert xref.cust_id == "000000001"
        assert xref.acct_id == "00000000002"
