# 💰 Payroll Automation System

A secure, production-ready payroll automation system built with FastAPI, Streamlit, and Paystack integration. This system enables automatic salary payments, worker management, and comprehensive audit trails with bank-level security.

## 🚀 Features

### Core Functionality
- **Secure Authentication**: Password + 2FA (Google Authenticator) login
- **Worker Management**: Complete CRUD operations for employee records
- **Automated Payments**: Scheduled salary payments via Paystack
- **Payment Processing**: Manual and automated payment processing
- **Real-time Dashboard**: Balance tracking and payment history
- **Audit Logging**: Complete activity tracking and security logs

### Security Features
- **Multi-factor Authentication**: TOTP-based 2FA with QR codes
- **Password Security**: bcrypt hashing with salt (12 rounds)
- **JWT Tokens**: Secure, stateless authentication
- **Rate Limiting**: API protection against abuse
- **Input Validation**: Comprehensive data sanitization
- **Audit Trail**: All actions logged with timestamps and IP addresses

### Payment Integration
- **Paystack API**: Nigerian bank account transfers
- **Account Verification**: Real-time bank account validation
- **Transfer Management**: Secure money transfers to Nigerian banks
- **Payment History**: Complete transaction records
- **Balance Monitoring**: Real-time Paystack account balance

## 🏗 Tech Stack

### Backend
- **FastAPI**: Modern, fast Python web framework
- **SQLAlchemy**: Database ORM with type safety
- **SQLite**: Lightweight database (development) / PostgreSQL (production)
- **APScheduler**: Job scheduling for automated payments
- **PyJWT**: JWT token management
- **bcrypt**: Password hashing
- **PyOTP**: TOTP 2FA implementation

### Frontend
- **Streamlit**: Python-based web application framework
- **Plotly**: Interactive charts and analytics
- **Pandas**: Data manipulation and analysis

### Payment Processing
- **Paystack**: Nigerian payment gateway
- **Bank Integration**: Support for all Nigerian banks

## 📁 Project Structure

```
payroll-automation-system/
├── backend/                     # FastAPI backend application
│   ├── auth/                   # Authentication & security
│   │   ├── security.py         # Password hashing, JWT tokens
│   │   ├── two-factor.py       # 2FA implementation
│   │   └── middleware.py       # Security middleware
│   ├── database.py             # Database configuration
│   ├── Config.py              # Application settings
│   ├── main.py                # Application entry point
│   ├── models/                # Database models
│   ├── routes/                # API endpoints
│   │   ├── auth.py            # Authentication routes
│   │   ├── worker.py          # Worker management routes
│   │   └── payment.py         # Payment processing routes
│   ├── services/              # Business logic
│   │   ├── paystack.py        # Paystack API wrapper
│   │   └── Payment_scheduler.py # Automated payment scheduler
│   └── utils/                 # Utility functions
│       └── validators.py      # Input validation
├── frontend/                   # Streamlit frontend
│   ├── app.py                 # Main application
│   ├── pages/
│   │   ├── balance.py         # Dashboard page
│   │   └── edit_salaries.py   # Worker management page
│   └── components/            # Reusable UI components
├── database/                   # Database files
│   ├── migrations/            # SQL migration scripts
│   └── seeds/                 # Initial data setup
├── scripts/                    # Utility scripts
│   ├── setup_db.py           # Database initialization
│   ├── create_user.py        # Admin user creation
│   └── backup_db.py          # Database backup utility
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
└── README.md                 # This file
```

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.8 or higher
- Git
- Paystack account (for payment processing)

### 1. Clone and Setup
```bash
# Clone the repository
git clone <repository-url>
cd payroll-automation-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings
nano .env
```

**Required Settings:**
- `SECRET_KEY`: Generate a secure secret key
- `PAYSTACK_SECRET_KEY`: Your Paystack secret key
- `PAYSTACK_PUBLIC_KEY`: Your Paystack public key
- `JWT_SECRET_KEY`: JWT signing secret

### 3. Database Setup
```bash
# Initialize database
python scripts/setup_db.py init

# Verify database setup
python scripts/setup_db.py status
```

### 4. Create Admin Users
```bash
# Create first admin user
python scripts/create_user.py create --username admin1 --email admin1@company.com

# Create second admin user
python scripts/create_user.py create --username admin2 --email admin2@company.com

# List all users
python scripts/create_user.py list
```

**Important**: Save the credentials file and QR code for 2FA setup!

### 5. Start the Application

**Terminal 1 - Backend API:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
streamlit run frontend/app.py --server.port 8501
```

### 6. Access the Application
- **Frontend**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## �� Payment System Usage

### Adding Workers
1. Login to the system with 2FA
2. Go to "Worker Management" tab
3. Click "Add Worker" and fill in:
   - Full name
   - Email (optional)
   - Bank details (automatically validated)
   - Salary amount
   - Payment frequency

### Processing Payments
1. **Manual Payment**: Select worker and process payment immediately
2. **Scheduled Payment**: Workers are automatically paid based on their frequency
3. **Bulk Payment**: Process multiple workers at once

### Payment History
- View all transaction records
- Filter by date, status, worker
- Export to CSV
- Track payment references

## 🔐 Security Configuration

### Password Policy
- Minimum 8 characters
- Must contain: uppercase, lowercase, digit, special character
- Prevents common weak passwords
- Secure hashing with bcrypt (12 rounds)

### Two-Factor Authentication (2FA)
- TOTP-based authentication
- Google Authenticator compatible
- QR code setup
- Backup codes for account recovery

### API Security
- JWT token authentication
- Rate limiting (100 requests/minute)
- Input validation and sanitization
- CORS protection
- SQL injection prevention

## 📊 Database Schema

### Core Tables

**Users Table**
- User accounts with 2FA support
- Password hashing and salt storage
- Login attempt tracking
- Audit trail integration

**Workers Table**
- Employee information
- Bank details and verification
- Salary and payment settings
- Payment scheduling

**Payment History Table**
- Complete transaction records
- Paystack integration details
- Status tracking (pending, success, failed)
- Audit trail integration

**Audit Logs Table**
- Security event tracking
- User action logging
- IP address recording
- Timestamp tracking

## 🔧 Configuration Options

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `true` |
| `DATABASE_URL` | Database connection | `sqlite:///./database/payroll.db` |
| `PAYSTACK_SECRET_KEY` | Paystack secret key | Required |
| `JWT_SECRET_KEY` | JWT signing secret | Required |
| `AUTO_PAYMENT_ENABLED` | Enable automated payments | `false` |
| `PAYMENT_SCHEDULE_HOUR` | Daily payment check hour | `9` |

### Paystack Configuration
1. Create account at https://paystack.com
2. Get API keys from dashboard
3. Add keys to `.env` file
4. Test with sandbox keys first

## 🛠 Development

### Running Tests
```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_auth.py

# Run with coverage
pytest --cov=backend
```

### Database Operations
```bash
# Reset database
python scripts/setup_db.py reset

# Backup database
python scripts/backup_db.py backup

# Restore database
python scripts/backup_db.py restore --file backups/payroll_backup_manual_20250101_120000.db.gz
```

### Code Quality
```bash
# Format code
black backend frontend scripts

# Sort imports
isort backend frontend scripts

# Lint code
flake8 backend frontend scripts

# Type checking
mypy backend
```

## 🚀 Deployment

### Production Deployment

**Requirements:**
- Python 3.8+
- PostgreSQL database
- Paystack production keys
- SSL certificate

**Steps:**
1. Set `DEBUG=false` in environment
2. Use PostgreSQL instead of SQLite
3. Configure proper database credentials
4. Set up SSL/TLS certificates
5. Configure reverse proxy (nginx)
6. Set up monitoring and logging

### Docker Deployment
```dockerfile
# Dockerfile example
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000 8501

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Cloud Deployment Options
- **Render**: Connect GitHub repo, set environment variables
- **Railway**: Simple deployment with database included
- **Heroku**: Traditional PaaS deployment
- **AWS/GCP/Azure**: Full cloud infrastructure

## 📈 Monitoring and Maintenance

### Health Checks
- API health: `GET /health`
- Database connectivity
- Payment scheduler status
- Paystack API status

### Logging
- Application logs: `./logs/payroll.log`
- Audit logs: Database `audit_logs` table
- Error tracking and alerting

### Backup Strategy
- Automated daily backups
- Compressed and encrypted storage
- 30-day retention policy
- Point-in-time recovery capability

## 🆘 Troubleshooting

### Common Issues

**Database Connection Error**
```bash
# Check database file permissions
ls -la database/payroll.db
# Reset database if corrupted
python scripts/setup_db.py reset
```

**Payment Processing Failed**
1. Verify Paystack API keys
2. Check account balance
3. Validate bank account details
4. Review error logs

**2FA Not Working**
1. Check system time synchronization
2. Verify QR code scan accuracy
3. Use backup codes if available
4. Reset 2FA for user account

**Frontend Connection Error**
1. Ensure backend is running on port 8000
2. Check CORS settings
3. Verify API endpoints are accessible

### Log Locations
- Application logs: `logs/payroll.log`
- Database logs: Check database file location
- Frontend logs: Browser developer console

## 📚 API Documentation

### Authentication Endpoints
- `POST /api/auth/login` - User login
- `POST /api/auth/verify-2fa` - 2FA verification
- `POST /api/auth/logout` - User logout

### Worker Management
- `GET /api/workers` - List workers
- `POST /api/workers` - Create worker
- `PUT /api/workers/{id}` - Update worker
- `DELETE /api/workers/{id}` - Delete worker

### Payment Processing
- `GET /api/payments/balance` - Get Paystack balance
- `POST /api/payments/process` - Process payment
- `GET /api/payments/history` - Payment history
- `GET /api/payments/stats` - Payment statistics

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to branch: `git push origin feature/new-feature`
5. Submit pull request

### Code Standards
- Follow PEP 8 style guidelines
- Write comprehensive tests
- Document new features
- Update README for major changes

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the documentation
- Review API documentation at `/docs`
- Check troubleshooting section
- Create GitHub issue for bugs

## 🔮 Future Enhancements

- **Multi-currency support**
- **Advanced reporting and analytics**
- **Email notifications**
- **Mobile application**
- **Third-party integrations**
- **Advanced scheduling options**
- **API rate limiting improvements**
- **Multi-tenant support**

---

**Built with ❤️ for secure payroll automation**
