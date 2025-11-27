"""Tests for Flask API."""

import pytest
import json
import tempfile
import os

from carddemo.api.app import create_app
from carddemo.services.data_store import DataStore
import carddemo.services.data_store as ds_module


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

        # Create cardxref
        cardxref = [
            {
                "card_num": "1234567890123456",
                "cust_id": "000000001",
                "acct_id": "00000000001",
            }
        ]
        with open(os.path.join(tmpdir, "cardxref.json"), "w") as f:
            json.dump(cardxref, f)

        # Create empty files for other data
        for filename in ["transactions.json", "customers.json"]:
            with open(os.path.join(tmpdir, filename), "w") as f:
                json.dump([], f)

        yield tmpdir


@pytest.fixture
def client(temp_data_dir):
    """Create a test client."""
    # Reset global data store
    ds_module._data_store = DataStore(temp_data_dir)

    # Reset auth service
    import carddemo.services.auth_service as auth_module
    auth_module._auth_service = None

    # Reset other services to use new data store
    import carddemo.services.account_service as acct_module
    import carddemo.services.transaction_service as tran_module
    import carddemo.services.user_service as user_module
    acct_module._account_service = None
    acct_module._card_service = None
    acct_module._customer_service = None
    tran_module._transaction_service = None
    tran_module._bill_payment_service = None
    user_module._user_service = None

    app = create_app(temp_data_dir)
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_token(client):
    """Get an authentication token."""
    response = client.post(
        "/api/auth/login",
        json={"user_id": "ADMIN001", "password": "PASSWORD"},
    )
    data = json.loads(response.data)
    return data["session"]["token"]


@pytest.fixture
def user_token(client):
    """Get a regular user authentication token."""
    response = client.post(
        "/api/auth/login",
        json={"user_id": "USER0001", "password": "PASSWORD"},
    )
    data = json.loads(response.data)
    return data["session"]["token"]


class TestHealthEndpoint:
    """Tests for health endpoint."""

    def test_health(self, client):
        """Test health endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert data["application"] == "CardDemo"


class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    def test_login_success(self, client):
        """Test successful login."""
        response = client.post(
            "/api/auth/login",
            json={"user_id": "ADMIN001", "password": "PASSWORD"},
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "session" in data
        assert data["session"]["user_id"] == "ADMIN001"
        assert data["session"]["is_admin"] is True

    def test_login_failure(self, client):
        """Test failed login."""
        response = client.post(
            "/api/auth/login",
            json={"user_id": "ADMIN001", "password": "WRONG"},
        )
        assert response.status_code == 401

    def test_logout(self, client, auth_token):
        """Test logout."""
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200

    def test_get_current_user(self, client, auth_token):
        """Test getting current user."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["user_id"] == "ADMIN001"


class TestAccountEndpoints:
    """Tests for account endpoints."""

    def test_list_accounts_unauthorized(self, client):
        """Test listing accounts without auth."""
        response = client.get("/api/accounts")
        assert response.status_code == 401

    def test_list_accounts(self, client, auth_token):
        """Test listing accounts."""
        response = client.get(
            "/api/accounts",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "accounts" in data
        assert data["total"] == 1

    def test_get_account(self, client, auth_token):
        """Test getting an account."""
        response = client.get(
            "/api/accounts/00000000001",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "account" in data
        assert data["account"]["acct_id"] == "00000000001"

    def test_get_account_not_found(self, client, auth_token):
        """Test getting a nonexistent account."""
        response = client.get(
            "/api/accounts/99999999999",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 404


class TestUserManagement:
    """Tests for user management endpoints."""

    def test_list_users_admin(self, client, auth_token):
        """Test listing users as admin."""
        response = client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "users" in data
        assert data["total"] == 2

    def test_list_users_non_admin(self, client, user_token):
        """Test listing users as non-admin (should fail)."""
        response = client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    def test_add_user(self, client, auth_token):
        """Test adding a user."""
        response = client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "user_id": "NEWUSER1",
                "password": "SECRET",
                "first_name": "New",
                "last_name": "User",
            },
        )
        assert response.status_code == 201


class TestTransactionEndpoints:
    """Tests for transaction endpoints."""

    def test_add_transaction(self, client, auth_token):
        """Test adding a transaction."""
        response = client.post(
            "/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "card_num": "1234567890123456",
                "amount": "50.00",
                "description": "Test purchase",
            },
        )
        assert response.status_code == 201

        data = json.loads(response.data)
        assert "transaction" in data
        assert data["transaction"]["amount"] == "50.00"

    def test_list_transactions(self, client, auth_token):
        """Test listing transactions."""
        # First add a transaction
        client.post(
            "/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "card_num": "1234567890123456",
                "amount": "25.00",
            },
        )

        response = client.get(
            "/api/transactions",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "transactions" in data


class TestPaymentEndpoints:
    """Tests for payment endpoints."""

    def test_make_payment(self, client, auth_token):
        """Test making a payment."""
        response = client.post(
            "/api/payments",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "acct_id": "00000000001",
                "amount": "100.00",
            },
        )
        assert response.status_code == 201

        data = json.loads(response.data)
        assert "transaction" in data
        # Payment should be a credit (negative amount)
        assert float(data["transaction"]["amount"]) < 0
