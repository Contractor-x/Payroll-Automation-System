from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./database/payroll.db"
    
    # Security
    secret_key: str = "your-super-secret-key-change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    max_login_attempts: int = 5
    login_lockout_seconds: int = 5
    
    # Paystack
    paystack_secret_key: str = "sk_test_your_paystack_secret_key_here"
    paystack_public_key: str = "pk_test_your_paystack_public_key_here"
    paystack_base_url: str = "https://api.paystack.co"
    
    # Application
    app_name: str = "Payroll Automation System"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # Scheduler
    payment_schedule_hour: int = 9
    auto_payment_enabled: bool = True
    
    # CORS
    cors_origins: List[str] = ["http://localhost:8501", "http://localhost:8000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_database_url() -> str:
    """Get database URL for SQLAlchemy"""
    return settings.database_url


def get_secret_key() -> str:
    """Get secret key for JWT and hashing"""
    return settings.secret_key
