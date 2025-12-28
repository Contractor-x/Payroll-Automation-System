#!/usr/bin/env python3
"""
Create admin user script for Payroll Automation System
Generates secure passwords, sets up 2FA, and creates QR codes
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
import qrcode
import base64
from io import BytesIO

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.database import SessionLocal, User
from backend.auth.security import hash_password, generate_secure_password, validate_password_strength
from backend.auth.two_factor import setup_two_factor_auth
from backend.Config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_admin_user(username: str, email: str, password: str = None, force_2fa: bool = True):
    """
    Create a new admin user with optional 2FA setup
    
    Args:
        username: Username for the admin
        email: Email address
        password: Password (will generate if None)
        force_2fa: Whether to require 2FA setup
        
    Returns:
        dict: User creation result with credentials and 2FA setup
    """
    db = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            logger.error(f"❌ User with username '{username}' or email '{email}' already exists")
            return None
        
        # Generate password if not provided
        if not password:
            password = generate_secure_password(16)
            logger.info("🔐 Generated secure password")
        
        # Validate password strength
        is_valid, issues = validate_password_strength(password)
        if not is_valid:
            logger.error(f"❌ Password validation failed: {'; '.join(issues)}")
            return None
        
        # Hash password
        password_hash, salt = hash_password(password)
        
        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            salt=salt,
            is_active=True,
            failed_login_attempts=0
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"✅ User '{username}' created successfully!")
        
        # Setup 2FA if required
        two_fa_data = None
        if force_2fa:
            try:
                two_fa_data = setup_two_factor_auth(username)
                user.totp_secret = two_fa_data["secret"]
                db.commit()
                logger.info("🔐 2FA setup completed")
            except Exception as e:
                logger.warning(f"⚠️ 2FA setup failed: {e}")
        
        # Create credentials file
        credentials_file = create_credentials_file(username, email, password, two_fa_data)
        
        return {
            "user_id": user.id,
            "username": username,
            "email": email,
            "password": password,
            "two_fa_enabled": two_fa_data is not None,
            "two_fa_secret": two_fa_data["secret"] if two_fa_data else None,
            "qr_code": two_fa_data["qr_code"] if two_fa_data else None,
            "backup_codes": two_fa_data["backup_codes"] if two_fa_data else [],
            "credentials_file": credentials_file
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to create user: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def create_credentials_file(username: str, email: str, password: str, two_fa_data: dict = None):
    """
    Create a secure credentials file for the user
    
    Args:
        username: Username
        email: Email address
        password: Plain text password
        two_fa_data: 2FA setup data
        
    Returns:
        str: Path to credentials file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"admin_credentials_{username}_{timestamp}.txt"
    filepath = project_root / "credentials" / filename
    
    # Create credentials directory
    filepath.parent.mkdir(exist_ok=True)
    
    content = f"""
PAYROLL AUTOMATION SYSTEM - ADMIN CREDENTIALS
============================================
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

LOGIN INFORMATION:
-----------------
Username: {username}
Email: {email}
Password: {password}

SECURITY SETUP:
--------------
2FA Enabled: {"Yes" if two_fa_data else "No"}

"""
    
    if two_fa_data:
        content += f"""
TWO-FACTOR AUTHENTICATION (2FA):
--------------------------------
Secret Key: {two_fa_data['secret']}
Backup Codes:
"""
        for i, code in enumerate(two_fa_data['backup_codes'], 1):
            content += f"  {i:2d}. {code}\n"
        
        content += f"""
QR Code: Available as base64 in separate file
Auth URI: {two_fa_data['auth_uri']}

SETUP INSTRUCTIONS:
------------------
1. Install Google Authenticator or compatible app
2. Scan QR code (see {filename.replace('.txt', '_qr.png')})
3. Or manually enter secret key: {two_fa_data['secret']}
4. Save backup codes in a secure location

IMPORTANT SECURITY NOTES:
------------------------
- Change the password after first login
- Keep backup codes in a secure, offline location
- Never share these credentials with anyone
- Delete this file after saving credentials securely
- Enable 2FA for additional security
"""
    else:
        content += """
2FA NOT CONFIGURED:
------------------
This account does not have 2FA enabled. For security reasons,
it is recommended to enable 2FA through the application interface.

To enable 2FA:
1. Login to the system
2. Go to account settings
3. Setup 2FA and scan QR code with Google Authenticator
"""
    
    # Write credentials file
    with open(filepath, 'w') as f:
        f.write(content)
    
    # Save QR code if 2FA is enabled
    if two_fa_data:
        qr_filename = filename.replace('.txt', '_qr.png')
        qr_filepath = project_root / "credentials" / qr_filename
        
        # Decode base64 QR code and save
        qr_data = two_fa_data['qr_code'].split(',')[1]  # Remove data:image/png;base64,
        qr_bytes = base64.b64decode(qr_data)
        
        with open(qr_filepath, 'wb') as f:
            f.write(qr_bytes)
        
        logger.info(f"📱 QR code saved: {qr_filepath}")
    
    logger.info(f"📄 Credentials file created: {filepath}")
    return str(filepath)


def list_users():
    """List all users in the system"""
    db = SessionLocal()
    
    try:
        users = db.query(User).all()
        
        if not users:
            print("📝 No users found in the system")
            return
        
        print(f"\n👥 SYSTEM USERS ({len(users)} total):")
        print("=" * 60)
        
        for user in users:
            status = "✅ Active" if user.is_active else "❌ Inactive"
            two_fa = "🔐 Enabled" if user.totp_secret else "⚠️ Disabled"
            last_login = user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "Never"
            
            print(f"""
Username: {user.username}
Email: {user.email}
Status: {status}
2FA: {two_fa}
Failed Login Attempts: {user.failed_login_attempts}
Last Login: {last_login}
Created: {user.created_at.strftime("%Y-%m-%d %H:%M")}
{'-' * 60}""")
            
    except Exception as e:
        logger.error(f"❌ Failed to list users: {e}")
    finally:
        db.close()


def reset_user_password(username: str):
    """Reset user password and generate new one"""
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            logger.error(f"❌ User '{username}' not found")
            return None
        
        # Generate new password
        new_password = generate_secure_password(16)
        
        # Hash new password
        password_hash, salt = hash_password(new_password)
        
        # Update user
        user.password_hash = password_hash
        user.salt = salt
        user.failed_login_attempts = 0  # Reset failed attempts
        db.commit()
        
        logger.info(f"✅ Password reset for user '{username}'")
        
        # Create new credentials file
        two_fa_data = None
        if user.totp_secret:
            # Recreate 2FA data for the credentials file
            from backend.auth.two_factor import two_factor
            two_fa_data = {
                "secret": user.totp_secret,
                "qr_code": two_factor.generate_qr_code(user.totp_secret, user.username),
                "backup_codes": two_factor.get_backup_codes(),
                "auth_uri": two_factor.get_auth_uri(user.totp_secret, user.username)
            }
        
        credentials_file = create_credentials_file(user.username, user.email, new_password, two_fa_data)
        
        return {
            "username": user.username,
            "email": user.email,
            "new_password": new_password,
            "credentials_file": credentials_file
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to reset password: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def main():
    """Main script entry point"""
    parser = argparse.ArgumentParser(description="Payroll System Admin User Management")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create user command
    create_parser = subparsers.add_parser("create", help="Create new admin user")
    create_parser.add_argument("--username", required=True, help="Username for the admin")
    create_parser.add_argument("--email", required=True, help="Email address")
    create_parser.add_argument("--password", help="Password (auto-generated if not provided)")
    create_parser.add_argument("--no-2fa", action="store_true", help="Disable 2FA requirement")
    
    # List users command
    subparsers.add_parser("list", help="List all users")
    
    # Reset password command
    reset_parser = subparsers.add_parser("reset-password", help="Reset user password")
    reset_parser.add_argument("--username", required=True, help="Username to reset password for")
    
    args = parser.parse_args()
    
    if args.command == "create":
        print("🚀 Creating admin user...")
        result = create_admin_user(
            username=args.username,
            email=args.email,
            password=args.password,
            force_2fa=not args.no_2fa
        )
        
        if result:
            print(f"\n✅ SUCCESS! Admin user created:")
            print(f"Username: {result['username']}")
            print(f"Email: {result['email']}")
            print(f"Password: {result['password']}")
            print(f"2FA Enabled: {'Yes' if result['two_fa_enabled'] else 'No'}")
            print(f"Credentials File: {result['credentials_file']}")
            
            if result['two_fa_enabled']:
                print(f"\n📱 2FA Setup Required:")
                print(f"1. Install Google Authenticator app")
                print(f"2. Scan QR code from credentials folder")
                print(f"3. Or manually enter secret: {result['two_fa_secret']}")
                print(f"4. Save backup codes securely")
            
            print(f"\n⚠️  IMPORTANT SECURITY NOTES:")
            print(f"- Change password after first login")
            print(f"- Keep credentials file secure and delete after use")
            print(f"- Save backup codes in secure, offline location")
        else:
            print("❌ Failed to create user")
            sys.exit(1)
    
    elif args.command == "list":
        list_users()
    
    elif args.command == "reset-password":
        print("🔄 Resetting user password...")
        result = reset_user_password(args.username)
        
        if result:
            print(f"\n✅ Password reset successful:")
            print(f"Username: {result['username']}")
            print(f"New Password: {result['new_password']}")
            print(f"Credentials File: {result['credentials_file']}")
        else:
            print("❌ Failed to reset password")
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
