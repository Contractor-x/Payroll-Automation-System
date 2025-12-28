from typing import Optional, List, Dict
import re
from pydantic import BaseModel, EmailStr, validator
from backend.database import NIGERIAN_BANK_CODES


class ValidationError(Exception):
    """Custom validation error"""
    pass


class BaseValidator:
    """Base validation class"""
    
    @staticmethod
    def validate_nigerian_phone(phone: str) -> bool:
        """Validate Nigerian phone number format"""
        # Remove common prefixes and spaces
        phone = re.sub(r'^(\+234|234|0)', '', phone)
        
        # Check if it's 10 digits and starts with valid Nigerian prefixes
        pattern = r'^(70[0-9]{8}|80[0-9]{8}|81[0-9]{8}|90[0-9]{8}|91[0-9]{8})$'
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def validate_account_number(account_number: str) -> bool:
        """Validate Nigerian bank account number"""
        # Should be 10 digits
        return bool(re.match(r'^\d{10}$', account_number))
    
    @staticmethod
    def validate_bank_code(bank_code: str) -> bool:
        """Validate Nigerian bank code"""
        return bank_code in NIGERIAN_BANK_CODES
    
    @staticmethod
    def sanitize_name(name: str) -> str:
        """Sanitize name input"""
        if not name:
            return ""
        
        # Remove extra whitespace and special characters
        cleaned = re.sub(r'[^\w\s\-\.]', '', name.strip())
        return ' '.join(cleaned.split())
    
    @staticmethod
    def validate_salary_amount(amount: float) -> bool:
        """Validate salary amount"""
        return 0 < amount <= 10000000  # Between 0 and 10 million Naira
    
    @staticmethod
    def validate_payment_frequency(frequency: str) -> bool:
        """Validate payment frequency"""
        valid_frequencies = ['weekly', 'bi-weekly', 'monthly']
        return frequency in valid_frequencies


class WorkerValidator(BaseValidator):
    """Worker-specific validation"""
    
    @staticmethod
    def validate_worker_data(data: Dict) -> Dict:
        """Validate complete worker data"""
        errors = []
        
        # Validate name
        if not data.get('name'):
            errors.append("Name is required")
        else:
            name = BaseValidator.sanitize_name(data['name'])
            if len(name) < 2:
                errors.append("Name must be at least 2 characters")
            data['name'] = name
        
        # Validate email (optional)
        email = data.get('email')
        if email:
            try:
                # Basic email validation
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                    errors.append("Invalid email format")
                data['email'] = email.lower().strip()
            except:
                errors.append("Invalid email format")
        
        # Validate bank code
        bank_code = data.get('bank_code')
        if not bank_code:
            errors.append("Bank code is required")
        elif not BaseValidator.validate_bank_code(bank_code):
            errors.append(f"Invalid bank code. Valid codes: {', '.join(list(NIGERIAN_BANK_CODES.keys())[:10])}...")
        
        # Validate account number
        account_number = data.get('account_number')
        if not account_number:
            errors.append("Account number is required")
        elif not BaseValidator.validate_account_number(account_number):
            errors.append("Account number must be exactly 10 digits")
        
        # Validate salary
        salary_amount = data.get('salary_amount')
        if salary_amount is None:
            errors.append("Salary amount is required")
        elif not BaseValidator.validate_salary_amount(salary_amount):
            errors.append("Salary amount must be between 0 and 10,000,000 Naira")
        
        # Validate payment frequency
        payment_frequency = data.get('payment_frequency', 'monthly')
        if not BaseValidator.validate_payment_frequency(payment_frequency):
            errors.append(f"Invalid payment frequency. Valid options: weekly, bi-weekly, monthly")
        
        return {
            'data': data,
            'valid': len(errors) == 0,
            'errors': errors
        }


class PaymentValidator(BaseValidator):
    """Payment-specific validation"""
    
    @staticmethod
    def validate_payment_data(data: Dict) -> Dict:
        """Validate payment processing data"""
        errors = []
        
        # Validate worker ID
        worker_id = data.get('worker_id')
        if not worker_id or not isinstance(worker_id, int) or worker_id <= 0:
            errors.append("Valid worker ID is required")
        
        # Validate amount (optional - uses worker salary if not provided)
        amount = data.get('amount')
        if amount is not None:
            if not isinstance(amount, (int, float)) or amount <= 0:
                errors.append("Amount must be a positive number")
            elif amount > 10000000:  # 10 million Naira max
                errors.append("Amount cannot exceed 10,000,000 Naira")
        
        return {
            'data': data,
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def validate_transfer_reason(reason: str) -> bool:
        """Validate transfer reason"""
        if not reason:
            return False
        
        # Reason should be between 1 and 100 characters
        return 1 <= len(reason) <= 100


class SecurityValidator(BaseValidator):
    """Security and authentication validation"""
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format"""
        if not username:
            return False
        
        # Username should be 3-50 characters, alphanumeric and underscores
        pattern = r'^[a-zA-Z0-9_]{3,50}$'
        return bool(re.match(pattern, username))
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict:
        """Enhanced password strength validation"""
        errors = []
        warnings = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters")
        elif len(password) < 12:
            warnings.append("Consider using a longer password (12+ characters)")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:,.<>?]', password):
            errors.append("Password must contain at least one special character")
        
        # Check for common weak passwords
        weak_patterns = [
            'password', '123456', 'qwerty', 'admin', 'letmein',
            'welcome', 'monkey', '123456789', 'abc123'
        ]
        
        if any(pattern in password.lower() for pattern in weak_patterns):
            errors.append("Password is too common")
        
        # Check for sequential characters
        if re.search(r'(012|123|234|345|456|567|678|789|890)', password):
            warnings.append("Avoid sequential characters in password")
        
        if re.search(r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', password.lower()):
            warnings.append("Avoid alphabetical sequences in password")
        
        score = 0
        if len(password) >= 12: score += 1
        if len(password) >= 16: score += 1
        if len(password) >= 20: score += 1
        if re.search(r'[a-z]', password) and re.search(r'[A-Z]', password): score += 1
        if re.search(r'\d', password): score += 1
        if re.search(r'[!@#$%^&*()_+\-=\[\]{};:,.<>?]', password): score += 1
        if not any(pattern in password.lower() for pattern in weak_patterns): score += 1
        
        strength_levels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong']
        strength = strength_levels[min(score, len(strength_levels) - 1)]
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'strength': strength,
            'score': score
        }


class APITimeoutValidator(BaseValidator):
    """API timeout and rate limiting validation"""
    
    @staticmethod
    def validate_timeout_seconds(timeout: int) -> bool:
        """Validate timeout value"""
        return 1 <= timeout <= 300  # Between 1 second and 5 minutes
    
    @staticmethod
    def validate_rate_limit(requests_per_minute: int) -> bool:
        """Validate rate limit value"""
        return 1 <= requests_per_minute <= 1000  # Between 1 and 1000 requests per minute


class DataSanitizer:
    """Data sanitization utilities"""
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Basic HTML sanitization"""
        if not text:
            return ""
        
        # Remove script tags and their content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove potentially dangerous tags
        dangerous_tags = ['script', 'object', 'embed', 'link', 'style', 'iframe', 'frame', 'frameset', 'noscript']
        for tag in dangerous_tags:
            text = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', text, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(f'<{tag}[^>]*/?>', '', text, flags=re.IGNORECASE)
        
        # Remove javascript: and data: URLs
        text = re.sub(r'javascript:[^"\']*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'data:[^"\']*', '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe file operations"""
        if not filename:
            return ""
        
        # Remove path traversal attempts
        filename = re.sub(r'\.\./', '', filename)
        
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250 - len(ext)] + ('.' + ext if ext else '')
        
        return filename.strip()
    
    @staticmethod
    def sanitize_currency(amount: float) -> float:
        """Sanitize currency amount"""
        if not isinstance(amount, (int, float)):
            return 0.0
        
        # Round to 2 decimal places
        return round(float(amount), 2)


# Export main validation functions
validate_worker = WorkerValidator.validate_worker_data
validate_payment = PaymentValidator.validate_payment_data
validate_password = SecurityValidator.validate_password_strength
sanitize_input = DataSanitizer.sanitize_html
