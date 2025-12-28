import bcrypt
import secrets
import string
from typing import Optional
from backend.Config import get_secret_key


def generate_salt() -> str:
    """Generate a cryptographically secure random salt"""
    return secrets.token_hex(32)  # 64 characters


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hash a password using bcrypt with salt

    Args:
        password: Plain text password
        salt: Optional salt (will generate if not provided)

    Returns:
        tuple: (hashed_password, salt)
    """
    if salt is None:
        salt = generate_salt()

    # Combine password with salt and truncate to 72 bytes (bcrypt limit)
    salted_password = f"{password}{salt}"[:72]

    # Hash with bcrypt (12 rounds = 4096 iterations)
    hashed = bcrypt.hashpw(
        salted_password.encode('utf-8'),
        bcrypt.gensalt(rounds=12)
    )

    return hashed.decode('utf-8'), salt


def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        password: Plain text password to verify
        hashed_password: Previously hashed password
        salt: Salt used in original hashing
        
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        # Combine and truncate to bcrypt's 72-byte input limit (same as hash_password)
        salted_password = f"{password}{salt}"[:72]
        return bcrypt.checkpw(
            salted_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def generate_secure_password(length: int = 16) -> str:
    """
    Generate a cryptographically secure random password
    
    Args:
        length: Password length (default: 16)
        
    Returns:
        str: Random secure password
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    # Ensure password has at least one of each type
    if not any(c.islower() for c in password):
        password = password[:-1] + secrets.choice(string.ascii_lowercase)
    if not any(c.isupper() for c in password):
        password = password[:-1] + secrets.choice(string.ascii_uppercase)
    if not any(c.isdigit() for c in password):
        password = password[:-1] + secrets.choice(string.digits)
    if not any(c in "!@#$%^&*" for c in password):
        password = password[:-1] + secrets.choice("!@#$%^&*")
    
    return password


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password strength
    
    Args:
        password: Password to validate
        
    Returns:
        tuple: (is_valid, list_of_issues)
    """
    issues = []
    
    if len(password) < 8:
        issues.append("Password must be at least 8 characters long")
    
    if len(password) > 128:
        issues.append("Password must be less than 128 characters")
    
    if not any(c.islower() for c in password):
        issues.append("Password must contain at least one lowercase letter")
    
    if not any(c.isupper() for c in password):
        issues.append("Password must contain at least one uppercase letter")
    
    if not any(c.isdigit() for c in password):
        issues.append("Password must contain at least one digit")
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        issues.append("Password must contain at least one special character")
    
    # Check for common weak passwords
    weak_passwords = [
        "password", "123456", "123456789", "qwerty", "abc123",
        "password123", "admin", "letmein", "welcome", "monkey"
    ]
    
    if password.lower() in weak_passwords:
        issues.append("Password is too common")
    
    return len(issues) == 0, issues


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage
    
    Args:
        api_key: API key to hash
        
    Returns:
        str: Hashed API key
    """
    return hash_password(api_key)[0]


def verify_api_key(api_key: str, hashed_api_key: str) -> bool:
    """
    Verify an API key against its hash
    
    Args:
        api_key: Plain text API key to verify
        hashed_api_key: Previously hashed API key
        
    Returns:
        bool: True if API key matches, False otherwise
    """
    # For API keys, we use a fixed salt for consistency
    # This is acceptable since API keys are already random and secure
    fixed_salt = get_secret_key()[:64]  # Use first 64 chars of secret key as salt
    return verify_password(api_key, hashed_api_key, fixed_salt)


def generate_backup_codes(count: int = 8) -> list[str]:
    """
    Generate backup codes for 2FA
    
    Args:
        count: Number of backup codes to generate (default: 8)
        
    Returns:
        list: List of backup codes
    """
    codes = []
    for _ in range(count):
        # Generate 8-digit codes
        code = ''.join(secrets.choice(string.digits) for _ in range(8))
        codes.append(code)
    
    return codes


def hash_backup_codes(codes: list[str]) -> list[str]:
    """
    Hash backup codes for secure storage
    
    Args:
        codes: List of backup codes
        
    Returns:
        list: List of hashed backup codes
    """
    hashed_codes = []
    for code in codes:
        hashed_code = hash_password(code)[0]
        hashed_codes.append(hashed_code)
    
    return hashed_codes


def verify_backup_code(code: str, hashed_codes: list[str], salt: str) -> tuple[bool, int]:
    """
    Verify a backup code against hashed codes
    
    Args:
        code: Backup code to verify
        hashed_codes: List of hashed backup codes
        salt: Salt used in hashing
        
    Returns:
        tuple: (is_valid, index_of_matching_code or -1)
    """
    for index, hashed_code in enumerate(hashed_codes):
        if verify_password(code, hashed_code, salt):
            return True, index
    
    return False, -1
