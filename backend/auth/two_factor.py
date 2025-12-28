import pyotp
import qrcode
import io
import base64
from typing import Optional, Tuple
from backend.Config import settings


class TwoFactorAuth:
    """TOTP-based Two-Factor Authentication handler"""
    
    def __init__(self):
        self.issuer_name = settings.app_name
        self.digits = 6
        self.period = 30  # 30-second windows
        self.algorithm = "SHA1"
    
    def generate_secret(self) -> str:
        """Generate a new TOTP secret key"""
        return pyotp.random_base32()
    
    def get_auth_uri(self, secret: str, username: str) -> str:
        """
        Generate TOTP authentication URI for QR code
        
        Args:
            secret: TOTP secret key
            username: Username for the account
            
        Returns:
            str: Authentication URI
        """
        return pyotp.totp.TOTP(secret, digits=self.digits, period=self.period, 
                             algorithm=self.algorithm).provisioning_uri(
            name=username,
            issuer_name=self.issuer_name
        )
    
    def generate_qr_code(self, secret: str, username: str) -> str:
        """
        Generate QR code as base64 string
        
        Args:
            secret: TOTP secret key
            username: Username for the account
            
        Returns:
            str: Base64 encoded QR code image
        """
        auth_uri = self.get_auth_uri(secret, username)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(auth_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def generate_totp_code(self, secret: str) -> str:
        """
        Generate current TOTP code
        
        Args:
            secret: TOTP secret key
            
        Returns:
            str: 6-digit TOTP code
        """
        totp = pyotp.TOTP(secret, digits=self.digits, period=self.period, 
                         algorithm=self.algorithm)
        return totp.now()
    
    def verify_totp_code(self, secret: str, code: str, 
                        tolerance: int = 1) -> bool:
        """
        Verify TOTP code with time tolerance
        
        Args:
            secret: TOTP secret key
            code: 6-digit code to verify
            tolerance: Number of time steps to accept (default: 1)
            
        Returns:
            bool: True if code is valid, False otherwise
        """
        totp = pyotp.TOTP(secret, digits=self.digits, period=self.period, 
                         algorithm=self.algorithm)
        
        # Check current code and previous/next codes (tolerance)
        return totp.verify(code, valid_window=tolerance)
    
    def get_remaining_seconds(self, secret: str) -> int:
        """
        Get remaining seconds until current TOTP expires
        
        Args:
            secret: TOTP secret key
            
        Returns:
            int: Seconds remaining (0-30)
        """
        totp = pyotp.TOTP(secret, digits=self.digits, period=self.period, 
                         algorithm=self.algorithm)
        
        current_time = totp.timecode(totp.time())
        next_time = totp.timecode(totp.time()) + 1
        
        return int((next_time - totp.time()) * self.period)
    
    def get_backup_codes(self, count: int = 8) -> list[str]:
        """
        Generate backup codes for 2FA recovery
        
        Args:
            count: Number of backup codes to generate
            
        Returns:
            list: List of backup codes
        """
        backup_codes = []
        for _ in range(count):
            # Generate 8-digit backup codes
            import secrets
            import string
            code = ''.join(secrets.choice(string.digits) for _ in range(8))
            backup_codes.append(code)
        
        return backup_codes
    
    def verify_backup_code(self, code: str, backup_codes: list[str]) -> bool:
        """
        Verify backup code (case-insensitive)
        
        Args:
            code: Backup code to verify
            backup_codes: List of valid backup codes
            
        Returns:
            bool: True if backup code is valid
        """
        return code in backup_codes
    
    def create_recovery_config(self, username: str) -> dict:
        """
        Create complete 2FA configuration for a user
        
        Args:
            username: Username for the account
            
        Returns:
            dict: Contains secret, qr_code, backup_codes, and auth_uri
        """
        secret = self.generate_secret()
        qr_code = self.generate_qr_code(secret, username)
        auth_uri = self.get_auth_uri(secret, username)
        backup_codes = self.get_backup_codes()
        
        return {
            "secret": secret,
            "qr_code": qr_code,
            "auth_uri": auth_uri,
            "backup_codes": backup_codes,
            "issuer": self.issuer_name,
            "digits": self.digits,
            "period": self.period
        }


# Global 2FA instance
two_factor = TwoFactorAuth()


def setup_two_factor_auth(username: str) -> dict:
    """
    Setup 2FA for a user
    
    Args:
        username: Username for the account
        
    Returns:
        dict: 2FA configuration with QR code and backup codes
    """
    return two_factor.create_recovery_config(username)


def verify_2fa_code(secret: str, code: str) -> bool:
    """
    Verify 2FA code
    
    Args:
        secret: TOTP secret key
        code: Code to verify
        
    Returns:
        bool: True if code is valid
    """
    return two_factor.verify_totp_code(secret, code)


def get_qr_code_data(secret: str, username: str) -> str:
    """
    Get QR code data URL for display
    
    Args:
        secret: TOTP secret key
        username: Username for the account
        
    Returns:
        str: Base64 encoded QR code image
    """
    return two_factor.generate_qr_code(secret, username)


def get_totp_time_left(secret: str) -> int:
    """
    Get remaining time for current TOTP code
    
    Args:
        secret: TOTP secret key
        
    Returns:
        int: Seconds remaining
    """
    return two_factor.get_remaining_seconds(secret)


def generate_totp_now(secret: str) -> str:
    """
    Generate current TOTP code (for testing)
    
    Args:
        secret: TOTP secret key
        
    Returns:
        str: Current 6-digit code
    """
    return two_factor.generate_totp_code(secret)
