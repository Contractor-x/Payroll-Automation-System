# Payroll Automation System

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Security](https://img.shields.io/badge/security-enterprise_grade-red.svg)

**Secure automated payroll system with Paystack integration**

[Features](#features) • [Quick Start](#quick-start) • [Project](#project-structure) • [Security Features](#security-features)

</div>
---

## Overview

A secure payroll automation system designed for managing worker payments through Paystack. Features top-grade security with bcrypt password hashing, TOTP two-factor authentication, and comprehensive audit logging.

### Features

- **Security**: bcrypt hashing (12 rounds) + unique salts, TOTP 2FA, JWT authentication
- **Automated Payments**: Schedule and process payments with approval workflows
- **Two Admin System**: Designed for exactly 2 authorized users with full access control
- **Real-Time Balance**: Live Paystack account balance monitoring
- **Complete Audit Trail**: Every action logged with timestamp and IP address
- **Simple Interface**: Clean Streamlit UI with just 2 pages (Balance & Salary Management)

---

## Tech Stack

```yaml
Backend:  FastAPI + SQLAlchemy + Paystack API
Frontend: Streamlit
Database: SQLite (or PostgreSQL)
Security: bcrypt + PyOTP + JWT
Scheduler: APScheduler
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Paystack account with API keys
- Google Authenticator (or compatible 2FA app)

<!-- ### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/payroll-automation-system.git
cd payroll-automation-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your Paystack keys

# Initialize database
python scripts/setup_db.py

# Create admin users
python scripts/create_user.py --username admin1 --email admin1@company.com
python scripts/create_user.py --username admin2 --email admin2@company.com
```

### Running the Application

```bash
# Terminal 1: Start Backend API
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start Frontend
streamlit run frontend/app.py --server.port 8501
```

Visit `http://localhost:8501` and login with your credentials.

---

## Usage
-->
### Dashboard (Balance Page)

- View current Paystack balance
- See pending payments requiring approval
- Review payment history with filters
- Approve/reject payment requests
- Export transaction reports

### Salary Management Page

- Add new workers with bank details
- Update worker salaries (changes are logged)
- Set payment frequency (monthly/bi-weekly/weekly)
- Activate/deactivate workers
- View salary change history

### Automated Payments

Payments are automatically processed based on schedule:
1. System checks for due payments daily at 9:00 AM
2. Creates payment requests for approval
3. After admin approval, sends funds via Paystack
4. Logs transaction and updates next payment date

---
<!--
## API Reference

### Authentication

```bash
# Login
POST /api/auth/login
{
  "username": "admin1",
  "password": "your_password"
}

# Verify 2FA
POST /api/auth/verify-2fa
{
  "temp_token": "...",
  "totp_code": "123456"
}
```

### Workers

```bash
# List all workers
GET /api/workers

# Add new worker
POST /api/workers
{
  "name": "John Doe",
  "bank_account": "0123456789",
  "bank_code": "058",
  "salary_amount": 150000
}

# Update salary
PUT /api/workers/{id}
{
  "salary_amount": 180000
}
```

### Payments

```bash
# Get balance
GET /api/payments/balance

# Process payment
POST /api/payments/process
{
  "worker_id": 1,
  "amount": 150000
}

# Payment history
GET /api/payments/history?start_date=2025-01-01&end_date=2025-12-31
```

---
-->
## Security Features

| Feature | Implementation |
|---------|----------------|
| Password Security | bcrypt (12 rounds) + unique salts per user |
| Two-Factor Auth | TOTP (RFC 6238) compatible with Google Authenticator |
| Session Management | JWT tokens with 30-minute expiry + refresh tokens |
| Rate Limiting | 5 login attempts per 15 minutes |
| Audit Logging | All actions logged with user, timestamp, and IP |
| API Security | CORS, CSRF protection, SQL injection prevention |

---
<!--
## Configuration

Key environment variables in `.env`:

```ini
# Database
DATABASE_URL=sqlite:///./database/payroll.db

# Security
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256

# Paystack
PAYSTACK_SECRET_KEY=sk_live_xxxxx
PAYSTACK_PUBLIC_KEY=pk_live_xxxxx

# Scheduler
PAYMENT_SCHEDULE_HOUR=9
AUTO_PAYMENT_ENABLED=false
```

---

## Deployment

### Option 1: PythonAnywhere

```bash
# Upload via Git
git push origin main

# Setup virtualenv and install requirements
# Configure WSGI file
# Set up scheduled tasks for payments
```

### Option 2: Render/Railway

```bash
# Connect GitHub repository
# Set environment variables in dashboard
# Deploy with automatic HTTPS
```
-->
---

## Project Structure

```
payroll-automation-system/
├── backend/              # FastAPI application
│   ├── auth/            # Security & authentication
│   ├── models/          # Database models
│   ├── routes/          # API endpoints
│   └── services/        # Paystack integration
├── frontend/            # Streamlit UI
│   ├── pages/           # Balance & Salary pages
│   └── components/      # Reusable UI components
├── database/            # SQLite database
├── scripts/             # Setup & utility scripts
└── tests/               # Automated tests
```

---

## Support

For issues or questions:
- Create an issue on GitHub
- Email: dada4ash@gmail.com

For security vulnerabilities:
- Email: dada4ash@gmail.com (private disclosure)

---

## License

MIT License - see [LICENSE](LICENSE) file for details

---

<div align="center">

**Built with Python, FastAPI, Streamlit & Paystack**

</div>
