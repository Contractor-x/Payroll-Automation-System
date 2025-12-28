from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from backend.database import get_db, User, AuditLog
from backend.Config import settings
from backend.auth.security import verify_password


# JWT Configuration
JWT_SECRET_KEY = settings.secret_key
JWT_ALGORITHM = settings.jwt_algorithm
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_access_token_expire_minutes

# Security scheme
security = HTTPBearer()


class TokenData:
    """Data class for JWT token payload"""
    def __init__(self, user_id: int, username: str, exp: datetime):
        self.user_id = user_id
        self.username = username
        self.exp = exp


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Data to encode in token
        expires_delta: Custom expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_temp_token(data: Dict[str, Any], expires_minutes: int = 10) -> str:
    """
    Create temporary token for 2FA verification
    
    Args:
        data: Data to encode in token
        expires_minutes: Token expiration in minutes (default: 10)
        
    Returns:
        str: Encoded temporary JWT token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "temp"
    })
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> TokenData:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token to verify
        token_type: Expected token type ("access" or "temp")
        
    Returns:
        TokenData: Decoded token data
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: int = payload.get("user_id")
        username: str = payload.get("username")
        exp: datetime = datetime.fromtimestamp(payload.get("exp"))
        token_type_from_token: str = payload.get("type")
        
        if user_id is None or username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if token_type_from_token != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if exp < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenData(user_id=user_id, username=username, exp=exp)
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security),
                    db: Session = Depends(get_db)) -> User:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        User: Current user object
        
    Raises:
        HTTPException: If user not found or token invalid
    """
    token_data = verify_token(credentials.credentials, "access")
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user (alias for get_current_user)
    
    Args:
        current_user: Current user from dependency
        
    Returns:
        User: Current active user
    """
    return current_user


class AuthMiddleware:
    """Custom middleware for additional authentication checks"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add custom authentication logic here if needed
            # For now, FastAPI's dependency system handles this
            pass
        
        await self.app(scope, receive, send)


def setup_middleware(app: FastAPI):
    """Setup all middleware for the FastAPI application"""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # GZip middleware for response compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Custom auth middleware
    app.add_middleware(AuthMiddleware)


def create_login_audit_log(db: Session, user: User, ip_address: str = None, 
                          action: str = "login", details: str = None):
    """
    Create audit log entry for login events
    
    Args:
        db: Database session
        user: User object
        ip_address: Client IP address
        action: Action performed
        details: Additional details
    """
    audit_log = AuditLog(
        user_id=user.id,
        action=action,
        details=details,
        ip_address=ip_address
    )
    
    db.add(audit_log)
    db.commit()


def increment_failed_attempts(db: Session, username: str):
    """
    Increment failed login attempts for rate limiting
    
    Args:
        db: Database session
        username: Username that failed login
    """
    user = db.query(User).filter(User.username == username).first()
    if user:
        user.failed_login_attempts += 1
        
        # Set lockout time if max attempts reached
        if user.failed_login_attempts >= settings.max_login_attempts:
            user.lockout_until = datetime.utcnow() + timedelta(seconds=settings.login_lockout_seconds)
        
        db.commit()


def reset_failed_attempts(db: Session, username: str):
    """
    Reset failed login attempts after successful login
    
    Args:
        db: Database session
        username: Username that logged in successfully
    """
    user = db.query(User).filter(User.username == username).first()
    if user:
        user.failed_login_attempts = 0
        user.lockout_until = None
        user.last_login = datetime.utcnow()
        db.commit()


def is_account_locked(user: User) -> bool:
    """
    Check if account is locked due to too many failed attempts
    
    Args:
        user: User object
        
    Returns:
        bool: True if account is locked
    """
    if user.failed_login_attempts >= settings.max_login_attempts:
        # Check if lockout has expired
        if user.lockout_until and user.lockout_until > datetime.utcnow():
            # Still locked
            return True
        elif user.lockout_until and user.lockout_until <= datetime.utcnow():
            # Lockout has expired, reset attempts
            user.failed_login_attempts = 0
            user.lockout_until = None
            return False
        else:
            # Lockout time not set, create lockout
            return True
    return False


def get_time_until_unlock(user: User) -> Optional[int]:
    """
    Get time until account unlock (if locked)
    
    Args:
        user: User object
        
    Returns:
        Optional[int]: Seconds until unlock, None if not locked
    """
    if not is_account_locked(user):
        return None
    
    if user.lockout_until and user.lockout_until > datetime.utcnow():
        # Calculate seconds remaining
        time_diff = user.lockout_until - datetime.utcnow()
        return max(0, int(time_diff.total_seconds()))
    
    return 0


def generate_refresh_token(user_id: int, username: str) -> str:
    """
    Generate refresh token for token renewal
    
    Args:
        user_id: User ID
        username: Username
        
    Returns:
        str: Refresh token
    """
    data = {
        "user_id": user_id,
        "username": username,
        "type": "refresh"
    }
    
    # Refresh tokens last longer (e.g., 7 days)
    expires_delta = timedelta(days=7)
    return create_access_token(data, expires_delta)


def verify_refresh_token(token: str) -> TokenData:
    """
    Verify refresh token
    
    Args:
        token: Refresh token to verify
        
    Returns:
        TokenData: Decoded token data
    """
    return verify_token(token, "refresh")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Database: {settings.database_url}")
    print(f"Debug mode: {settings.debug}")
    
    yield
    
    # Shutdown
    print("Shutting down application...")
