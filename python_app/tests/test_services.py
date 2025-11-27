"""Tests for services."""

import pytest
import tempfile
import json
import os
from decimal import Decimal

from carddemo.models.user import User
from carddemo.models.account import Account
from carddemo.models.card import Card
from carddemo.services.data_store import DataStore
from carddemo.services.auth_service import AuthService
from carddemo.services.account_service import AccountService, CardService
from carddemo.services.transaction_service import TransactionService


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory with sample data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample users
        users = [
            {
                "user_id": "ADMIN001",
                "first_name": "Admin",
                "last_name": "User",
                "password": "PASSWORD",
                "user_type": "A",
            },
            {
                "user_id": "USER0001",
                "first_name": "Regular",
                "last_name": "User",
                "password": "PASSWORD",
                "user_type": "U",
            },
        ]
        with open(os.path.join(tmpdir, "users.json"), "w") as f:
            json.dump(users, f)

        # Create sample accounts
        accounts = [
            {
                "acct_id": "00000000001",
                "active_status": "Y",
                "curr_bal": "1000.00",
                "credit_limit": "5000.00",
                "cash_credit_limit": "2000.00",
            },
            {
                "acct_id": "00000000002",
                "active_status": "Y",
                "curr_bal": "2000.00",
                "credit_limit": "10000.00",
                "cash_credit_limit": "3000.00",
            },
        ]
        with open(os.path.join(tmpdir, "accounts.json"), "w") as f:
            json.dump(accounts, f)

        # Create sample cards
        cards = [
            {
                "card_num": "1234567890123456",
                "acct_id": "00000000001",
                "cvv_cd": "123",
                "embossed_name": "Test User",
                "expiration_date": "2030-12-31",
                "active_status": "Y",
            },
        ]
        with open(os.path.join(tmpdir, "cards.json"), "w") as f:
            json.dump(cards, f)

        # Create empty files for other data
        for filename in ["transactions.json", "customers.json", "cardxref.json"]:
            with open(os.path.join(tmpdir, filename), "w") as f:
                json.dump([], f)

        # Create cardxref for the card
        cardxref = [
            {
                "card_num": "1234567890123456",
                "cust_id": "000000001",
                "acct_id": "00000000001",
            }
        ]
        with open(os.path.join(tmpdir, "cardxref.json"), "w") as f:
            json.dump(cardxref, f)

        yield tmpdir


class TestDataStore:
    """Tests for DataStore."""

    def test_get_users(self, temp_data_dir):
        """Test getting users."""
        store = DataStore(temp_data_dir)
        users = store.get_users()

        assert len(users) == 2
        assert users[0].user_id == "ADMIN001"

    def test_get_user(self, temp_data_dir):
        """Test getting a specific user."""
        store = DataStore(temp_data_dir)
        user = store.get_user("ADMIN001")

        assert user is not None
        assert user.user_id == "ADMIN001"
        assert user.is_admin is True

    def test_get_nonexistent_user(self, temp_data_dir):
        """Test getting a nonexistent user."""
        store = DataStore(temp_data_dir)
        user = store.get_user("NONEXISTENT")

        assert user is None

    def test_save_user(self, temp_data_dir):
        """Test saving a user."""
        store = DataStore(temp_data_dir)

        new_user = User(
            user_id="NEWUSER1",
            first_name="New",
            last_name="User",
            password="SECRET",
            user_type="U",
        )
        store.save_user(new_user)

        # Verify the user was saved
        retrieved = store.get_user("NEWUSER1")
        assert retrieved is not None
        assert retrieved.first_name == "New"

    def test_get_accounts(self, temp_data_dir):
        """Test getting accounts."""
        store = DataStore(temp_data_dir)
        accounts = store.get_accounts()

        assert len(accounts) == 2

    def test_get_account(self, temp_data_dir):
        """Test getting a specific account."""
        store = DataStore(temp_data_dir)
        account = store.get_account("00000000001")

        assert account is not None
        assert account.curr_bal == Decimal("1000.00")


class TestAuthService:
    """Tests for AuthService."""

    def test_login_success(self, temp_data_dir):
        """Test successful login."""
        # Reset global data store
        import carddemo.services.data_store as ds_module
        ds_module._data_store = DataStore(temp_data_dir)

        service = AuthService()
        success, session, message = service.login("ADMIN001", "PASSWORD")

        assert success is True
        assert session is not None
        assert session.is_admin is True

    def test_login_wrong_password(self, temp_data_dir):
        """Test login with wrong password."""
        import carddemo.services.data_store as ds_module
        ds_module._data_store = DataStore(temp_data_dir)

        service = AuthService()
        success, session, message = service.login("ADMIN001", "WRONG")

        assert success is False
        assert session is None
        assert "Wrong Password" in message

    def test_login_user_not_found(self, temp_data_dir):
        """Test login with nonexistent user."""
        import carddemo.services.data_store as ds_module
        ds_module._data_store = DataStore(temp_data_dir)

        service = AuthService()
        success, session, message = service.login("NONEXIST", "PASSWORD")

        assert success is False
        assert "not found" in message

    def test_validate_session(self, temp_data_dir):
        """Test session validation."""
        import carddemo.services.data_store as ds_module
        ds_module._data_store = DataStore(temp_data_dir)

        service = AuthService()
        success, session, _ = service.login("ADMIN001", "PASSWORD")

        # Validate the session
        validated = service.validate_session(session.token)
        assert validated is not None
        assert validated.user_id == "ADMIN001"

    def test_logout(self, temp_data_dir):
        """Test logout."""
        import carddemo.services.data_store as ds_module
        ds_module._data_store = DataStore(temp_data_dir)

        service = AuthService()
        success, session, _ = service.login("ADMIN001", "PASSWORD")

        # Logout
        service.logout(session.token)

        # Session should be invalid
        validated = service.validate_session(session.token)
        assert validated is None


class TestAccountService:
    """Tests for AccountService."""

    def test_list_accounts(self, temp_data_dir):
        """Test listing accounts."""
        import carddemo.services.data_store as ds_module
        ds_module._data_store = DataStore(temp_data_dir)

        service = AccountService()
        accounts, total = service.list_accounts()

        assert total == 2
        assert len(accounts) == 2

    def test_get_account(self, temp_data_dir):
        """Test getting an account."""
        import carddemo.services.data_store as ds_module
        ds_module._data_store = DataStore(temp_data_dir)

        service = AccountService()
        account = service.get_account("00000000001")

        assert account is not None
        assert account.curr_bal == Decimal("1000.00")

    def test_update_account(self, temp_data_dir):
        """Test updating an account."""
        import carddemo.services.data_store as ds_module
        ds_module._data_store = DataStore(temp_data_dir)

        service = AccountService()
        success, message = service.update_account(
            "00000000001",
            credit_limit=Decimal("7500.00"),
        )

        assert success is True

        # Verify the update
        account = service.get_account("00000000001")
        assert account.credit_limit == Decimal("7500.00")


class TestTransactionService:
    """Tests for TransactionService."""

    def test_add_transaction(self, temp_data_dir):
        """Test adding a transaction."""
        import carddemo.services.data_store as ds_module
        ds_module._data_store = DataStore(temp_data_dir)

        service = TransactionService()
        success, transaction, message = service.add_transaction(
            card_num="1234567890123456",
            amount=Decimal("50.00"),
            description="Test purchase",
        )

        assert success is True
        assert transaction is not None
        assert transaction.amount == Decimal("50.00")

    def test_add_transaction_invalid_card(self, temp_data_dir):
        """Test adding a transaction with invalid card."""
        import carddemo.services.data_store as ds_module
        ds_module._data_store = DataStore(temp_data_dir)

        service = TransactionService()
        success, transaction, message = service.add_transaction(
            card_num="9999999999999999",
            amount=Decimal("50.00"),
        )

        assert success is False
        assert "Invalid card" in message
