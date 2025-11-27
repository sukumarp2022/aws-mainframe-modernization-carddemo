"""
CardDemo Flask Web API.

This module provides a RESTful API for the CardDemo application,
replacing the CICS transaction interface from the mainframe.
"""


from datetime import datetime
from decimal import Decimal
from functools import wraps
from typing import Callable, Optional

from flask import Flask, jsonify, request, g
from flask_cors import CORS

from ..services.auth_service import get_auth_service
from ..services.account_service import (
    get_account_service,
    get_card_service,
    get_customer_service,
)
from ..services.transaction_service import (
    get_transaction_service,
    get_bill_payment_service,
)
from ..services.user_service import get_user_service
from ..services.data_store import get_data_store


def create_app(data_dir: Optional[str] = None) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        data_dir: Optional data directory path

    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    CORS(app)

    # Configure data store
    if data_dir:
        get_data_store(data_dir)

    # Request helpers
    def get_token() -> Optional[str]:
        """Get auth token from request headers."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None

    def require_auth(f: Callable) -> Callable:
        """Decorator to require authentication."""

        @wraps(f)
        def decorated(*args, **kwargs):
            token = get_token()
            if not token:
                return jsonify({"error": "Authentication required"}), 401

            auth_service = get_auth_service()
            session = auth_service.validate_session(token)
            if not session:
                return jsonify({"error": "Invalid or expired session"}), 401

            g.session = session
            g.user = auth_service.get_current_user(token)
            return f(*args, **kwargs)

        return decorated

    def require_admin(f: Callable) -> Callable:
        """Decorator to require admin privileges."""

        @wraps(f)
        @require_auth
        def decorated(*args, **kwargs):
            if not g.session.is_admin:
                return jsonify({"error": "Admin privileges required"}), 403
            return f(*args, **kwargs)

        return decorated

    # Health check endpoint
    @app.route("/api/health")
    def health():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "application": "CardDemo",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
        })

    # Authentication endpoints
    @app.route("/api/auth/login", methods=["POST"])
    def login():
        """
        User login endpoint.

        Request body:
            user_id: User ID
            password: Password

        Returns:
            Session token and user info on success
        """
        data = request.get_json() or {}
        user_id = data.get("user_id", "")
        password = data.get("password", "")

        auth_service = get_auth_service()
        success, session, message = auth_service.login(user_id, password)

        if not success:
            return jsonify({"error": message}), 401

        return jsonify({
            "message": message,
            "session": session.to_dict(),
        })

    @app.route("/api/auth/logout", methods=["POST"])
    @require_auth
    def logout():
        """Log out current session."""
        token = get_token()
        auth_service = get_auth_service()
        auth_service.logout(token)
        return jsonify({"message": "Logged out successfully"})

    @app.route("/api/auth/me")
    @require_auth
    def get_current_user():
        """Get current user info."""
        return jsonify(g.user.to_dict())

    # Account endpoints
    @app.route("/api/accounts")
    @require_auth
    def list_accounts():
        """List all accounts with pagination."""
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 10, type=int)
        active_only = request.args.get("active_only", "false").lower() == "true"

        account_service = get_account_service()
        accounts, total = account_service.list_accounts(page, page_size, active_only)

        return jsonify({
            "accounts": [a.to_dict() for a in accounts],
            "total": total,
            "page": page,
            "page_size": page_size,
        })

    @app.route("/api/accounts/<acct_id>")
    @require_auth
    def get_account(acct_id: str):
        """Get account details."""
        account_service = get_account_service()
        details = account_service.get_account_details(acct_id)

        if not details:
            return jsonify({"error": "Account not found"}), 404

        return jsonify(details)

    @app.route("/api/accounts/<acct_id>", methods=["PUT"])
    @require_auth
    def update_account(acct_id: str):
        """Update account."""
        data = request.get_json() or {}

        account_service = get_account_service()
        success, message = account_service.update_account(
            acct_id=acct_id,
            active_status=data.get("active_status"),
            credit_limit=Decimal(data["credit_limit"]) if "credit_limit" in data else None,
            cash_credit_limit=Decimal(data["cash_credit_limit"]) if "cash_credit_limit" in data else None,
            group_id=data.get("group_id"),
        )

        if not success:
            return jsonify({"error": message}), 400

        return jsonify({"message": message})

    @app.route("/api/accounts/<acct_id>/balance")
    @require_auth
    def get_account_balance(acct_id: str):
        """Get account balance summary."""
        account_service = get_account_service()
        balance = account_service.get_account_balance(acct_id)

        if not balance:
            return jsonify({"error": "Account not found"}), 404

        return jsonify(balance)

    # Card endpoints
    @app.route("/api/cards")
    @require_auth
    def list_cards():
        """List cards with optional account filter."""
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 10, type=int)
        acct_id = request.args.get("acct_id")

        card_service = get_card_service()
        cards, total = card_service.list_cards(acct_id, page, page_size)

        return jsonify({
            "cards": [c.to_dict() for c in cards],
            "total": total,
            "page": page,
            "page_size": page_size,
        })

    @app.route("/api/cards/<card_num>")
    @require_auth
    def get_card(card_num: str):
        """Get card details."""
        card_service = get_card_service()
        details = card_service.get_card_details(card_num)

        if not details:
            return jsonify({"error": "Card not found"}), 404

        return jsonify(details)

    @app.route("/api/cards/<card_num>", methods=["PUT"])
    @require_auth
    def update_card(card_num: str):
        """Update card."""
        data = request.get_json() or {}

        card_service = get_card_service()
        success, message = card_service.update_card(
            card_num=card_num,
            active_status=data.get("active_status"),
            embossed_name=data.get("embossed_name"),
        )

        if not success:
            return jsonify({"error": message}), 400

        return jsonify({"message": message})

    # Customer endpoints
    @app.route("/api/customers")
    @require_auth
    def list_customers():
        """List customers with pagination."""
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 10, type=int)

        customer_service = get_customer_service()
        customers, total = customer_service.list_customers(page, page_size)

        return jsonify({
            "customers": [c.to_dict() for c in customers],
            "total": total,
            "page": page,
            "page_size": page_size,
        })

    @app.route("/api/customers/<cust_id>")
    @require_auth
    def get_customer(cust_id: str):
        """Get customer details."""
        customer_service = get_customer_service()
        customer = customer_service.get_customer(cust_id)

        if not customer:
            return jsonify({"error": "Customer not found"}), 404

        return jsonify(customer.to_dict())

    # Transaction endpoints
    @app.route("/api/transactions")
    @require_auth
    def list_transactions():
        """List transactions with filtering and pagination."""
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 10, type=int)
        card_num = request.args.get("card_num")
        acct_id = request.args.get("acct_id")

        start_date = None
        end_date = None
        if request.args.get("start_date"):
            start_date = datetime.fromisoformat(request.args["start_date"])
        if request.args.get("end_date"):
            end_date = datetime.fromisoformat(request.args["end_date"])

        transaction_service = get_transaction_service()
        transactions, total = transaction_service.list_transactions(
            card_num=card_num,
            acct_id=acct_id,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )

        return jsonify({
            "transactions": [t.to_dict() for t in transactions],
            "total": total,
            "page": page,
            "page_size": page_size,
        })

    @app.route("/api/transactions/<tran_id>")
    @require_auth
    def get_transaction(tran_id: str):
        """Get transaction details."""
        transaction_service = get_transaction_service()
        transaction = transaction_service.get_transaction(tran_id)

        if not transaction:
            return jsonify({"error": "Transaction not found"}), 404

        return jsonify(transaction.to_dict())

    @app.route("/api/transactions", methods=["POST"])
    @require_auth
    def add_transaction():
        """Add a new transaction."""
        data = request.get_json() or {}

        required_fields = ["card_num", "amount"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        transaction_service = get_transaction_service()
        success, transaction, message = transaction_service.add_transaction(
            card_num=data["card_num"],
            amount=Decimal(str(data["amount"])),
            type_cd=data.get("type_cd", "01"),
            cat_cd=data.get("cat_cd", "0000"),
            description=data.get("description", ""),
            merchant_name=data.get("merchant_name", ""),
            merchant_city=data.get("merchant_city", ""),
            merchant_zip=data.get("merchant_zip", ""),
            source=data.get("source", "Online"),
        )

        if not success:
            return jsonify({"error": message}), 400

        return jsonify({
            "message": message,
            "transaction": transaction.to_dict(),
        }), 201

    @app.route("/api/transactions/summary/<acct_id>")
    @require_auth
    def get_transaction_summary(acct_id: str):
        """Get transaction summary for an account."""
        start_date = None
        end_date = None
        if request.args.get("start_date"):
            start_date = datetime.fromisoformat(request.args["start_date"])
        if request.args.get("end_date"):
            end_date = datetime.fromisoformat(request.args["end_date"])

        transaction_service = get_transaction_service()
        summary = transaction_service.get_transaction_summary(
            acct_id=acct_id,
            start_date=start_date,
            end_date=end_date,
        )

        return jsonify(summary)

    # Bill payment endpoint
    @app.route("/api/payments", methods=["POST"])
    @require_auth
    def make_payment():
        """Make a bill payment."""
        data = request.get_json() or {}

        required_fields = ["acct_id", "amount"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        payment_service = get_bill_payment_service()
        success, transaction, message = payment_service.make_payment(
            acct_id=data["acct_id"],
            amount=Decimal(str(data["amount"])),
            source=data.get("source", "Online Payment"),
        )

        if not success:
            return jsonify({"error": message}), 400

        return jsonify({
            "message": message,
            "transaction": transaction.to_dict() if transaction else None,
        }), 201

    # User management endpoints (admin only)
    @app.route("/api/users")
    @require_admin
    def list_users():
        """List users (admin only)."""
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 10, type=int)

        user_service = get_user_service()
        users, total = user_service.list_users(page, page_size)

        return jsonify({
            "users": [u.to_dict() for u in users],
            "total": total,
            "page": page,
            "page_size": page_size,
        })

    @app.route("/api/users/<user_id>")
    @require_admin
    def get_user(user_id: str):
        """Get user details (admin only)."""
        user_service = get_user_service()
        user = user_service.get_user(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify(user.to_dict())

    @app.route("/api/users", methods=["POST"])
    @require_admin
    def add_user():
        """Add a new user (admin only)."""
        data = request.get_json() or {}

        required_fields = ["user_id", "password"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        user_service = get_user_service()
        success, message = user_service.add_user(
            user_id=data["user_id"],
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            user_type=data.get("user_type", "U"),
        )

        if not success:
            return jsonify({"error": message}), 400

        return jsonify({"message": message}), 201

    @app.route("/api/users/<user_id>", methods=["PUT"])
    @require_admin
    def update_user(user_id: str):
        """Update a user (admin only)."""
        data = request.get_json() or {}

        user_service = get_user_service()
        success, message = user_service.update_user(
            user_id=user_id,
            password=data.get("password"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            user_type=data.get("user_type"),
        )

        if not success:
            return jsonify({"error": message}), 400

        return jsonify({"message": message})

    @app.route("/api/users/<user_id>", methods=["DELETE"])
    @require_admin
    def delete_user(user_id: str):
        """Delete a user (admin only)."""
        user_service = get_user_service()
        success, message = user_service.delete_user(user_id)

        if not success:
            return jsonify({"error": message}), 400

        return jsonify({"message": message})

    # Reference data endpoints
    @app.route("/api/reference/transaction-types")
    @require_auth
    def get_transaction_types():
        """Get transaction types."""
        transaction_service = get_transaction_service()
        types = transaction_service.get_transaction_types()
        return jsonify([t.to_dict() for t in types])

    @app.route("/api/reference/transaction-categories")
    @require_auth
    def get_transaction_categories():
        """Get transaction categories."""
        transaction_service = get_transaction_service()
        categories = transaction_service.get_transaction_categories()
        return jsonify([c.to_dict() for c in categories])

    return app


def main():
    """Main entry point for the API server."""
    import argparse

    parser = argparse.ArgumentParser(description="CardDemo API Server")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to bind to (default: 5000)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    parser.add_argument(
        "--data-dir",
        help="Data directory path",
    )

    args = parser.parse_args()

    app = create_app(args.data_dir)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
