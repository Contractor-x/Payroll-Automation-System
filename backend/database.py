from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Numeric, Text, ForeignKey, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
import os

from backend.Config import get_database_url

# Create SQLAlchemy engine and session
engine = create_engine(
    get_database_url(),
    echo=False,  # Set to True for SQL query debugging
    connect_args={"check_same_thread": False} if "sqlite" in get_database_url() else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(64), nullable=False)
    totp_secret = Column(String(32), nullable=True)
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0)
    lockout_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")
    approved_payments = relationship("PaymentHistory", back_populates="approved_by_user", foreign_keys="PaymentHistory.approved_by")


class Worker(Base):
    __tablename__ = "workers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    bank_name = Column(String(100), nullable=False)
    account_number = Column(String(20), nullable=False)
    bank_code = Column(String(10), nullable=False)
    salary_amount = Column(Numeric(10, 2), nullable=False)
    payment_frequency = Column(String(20), default="monthly")  # monthly, bi-weekly, weekly
    last_paid = Column(DateTime, nullable=True)
    next_payment_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    payment_history = relationship("PaymentHistory", back_populates="worker")


class PaymentHistory(Base):
    __tablename__ = "payment_history"
    
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False)  # success, failed, pending, cancelled
    transaction_reference = Column(String(100), nullable=True)
    paystack_reference = Column(String(100), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    worker = relationship("Worker", back_populates="payment_history")
    approved_by_user = relationship("User", back_populates="approved_payments", foreign_keys=[approved_by])


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")


# Database utility functions
def get_db() -> Session:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)


def get_db_session() -> Session:
    """Get a new database session"""
    return SessionLocal()


def init_db():
    """Initialize database with tables"""
    create_tables()


# Bank codes for Nigerian banks
NIGERIAN_BANK_CODES = {
    "044": "Access Bank",
    "063": "BankFirst",
    "050": "Ecobank",
    "030": "FCMB",
    "057": "FCMB Bank",
    "014": "First Bank",
    "011": "First Bank of Nigeria",
    "070": "Fidelity Bank",
    "058": "Guaranty Trust Bank",
    "069": "Intercontinental Bank",
    "082": "Keystone Bank",
    "090": "Providus Bank",
    "076": "Polaris Bank",
    "088": "Sterling Bank",
    "232": "Sterling Bank",
    "101": "SunTrust Bank",
    "032": "Union Bank",
    "033": "United Bank for Africa",
    "057": "Unity Bank",
    "032": "Wema Bank",
    "057": "Access Bank",
    "50383": "PiggyVest",
    "999991": "VFD Microfinance Bank",
    "51204": "Moniepoint MFB",
    "50257": "Opay",
    "307": "Kuda Bank",
    "50311": "Carbon",
    "50135": "FairMoney",
    "901": "ALAT by Wema Bank",
    "565": "RubiBank",
    "51227": "Mint MFB",
    "10004": "Safe Haven MFB",
    "120001": "Migo MFB",
    "10003": "NPF MFB",
    "10001": "FSDH MFB",
    "10002": "Seed Capital MFB",
    "10005": "Trust MFB",
    "10006": "Stella MFB",
    "10007": "Crescent MFB",
    "10008": "FullRange MFB",
    "10009": "Boctrust MFB",
    "10010": "Conal MFB",
    "10011": "Royal Exchange MFB",
    "10012": "Gateway MFB",
    "10013": "Lapo MFB",
    "10014": "Addosser MFB",
    "10015": "New Prudential MFB",
    "10016": "Covenant MFB",
    "10017": "Progress MFB",
    "10018": "Imperial MFB",
    "10019": "Infinity MFB",
    "10020": "KCM MFB",
    "10021": "Chase MFB",
    "10022": "Rephidim MFB",
    "10023": "Sunshine MFB",
    "10024": "Fiduciary MFB",
    "10025": "Richway MFB",
    "10026": "Niger MFB",
    "10027": "First MFB",
    "10028": "Trust Fund MFB",
    "10029": "Oak MFB",
    "10030": "Pioneer MFB"
}
