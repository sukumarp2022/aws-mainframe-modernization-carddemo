# CardDemo - Python Modernized Application

A modernized Python implementation of the CardDemo mainframe credit card management application.

## Overview

This Python application is a complete modernization of the original COBOL/CICS mainframe CardDemo application. It provides the same functionality including:

- User authentication and authorization
- Account management
- Credit card management
- Transaction processing
- Bill payments
- Interest calculations
- Statement generation
- Batch processing

## Installation

```bash
cd python_app
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Running the Application

### Web API Server
```bash
carddemo-api
```
Or:
```bash
python -m carddemo.api.app
```

### Batch Processing
```bash
carddemo-batch --job <job_name>
```
Available jobs: `post_transactions`, `calculate_interest`, `generate_statements`

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login

### Accounts
- `GET /api/accounts` - List accounts
- `GET /api/accounts/<id>` - View account details
- `PUT /api/accounts/<id>` - Update account

### Cards
- `GET /api/cards` - List credit cards
- `GET /api/cards/<card_num>` - View card details
- `PUT /api/cards/<card_num>` - Update card

### Transactions
- `GET /api/transactions` - List transactions
- `POST /api/transactions` - Add transaction
- `GET /api/transactions/<id>` - View transaction details

### Users (Admin only)
- `GET /api/users` - List users
- `POST /api/users` - Add user
- `PUT /api/users/<id>` - Update user
- `DELETE /api/users/<id>` - Delete user

## Data Migration

Sample data files are provided in the `data/` directory in JSON format, migrated from the original mainframe flat files.

## Testing

```bash
pytest
```

With coverage:
```bash
pytest --cov=carddemo
```

## License

Apache License 2.0
