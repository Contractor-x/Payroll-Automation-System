import requests
from typing import Dict, Optional, Tuple
from backend.Config import settings
import logging

logger = logging.getLogger(__name__)


class PaystackService:
    """
    Paystack API service for handling payments and account operations
    """
    
    def __init__(self):
        self.base_url = settings.paystack_base_url
        self.secret_key = settings.paystack_secret_key
        self.public_key = settings.paystack_public_key
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    def get_balance(self) -> Dict:
        """
        Get current account balance
        
        Returns:
            Dict: Balance information or raises exception
        """
        try:
            response = requests.get(
                f"{self.base_url}/balance",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack balance check failed: {e}")
            raise Exception(f"Unable to retrieve balance: {str(e)}")
    
    def resolve_account(self, account_number: str, bank_code: str) -> Dict:
        """
        Resolve bank account details
        
        Args:
            account_number: Bank account number
            bank_code: Nigerian bank code
            
        Returns:
            Dict: Account details or raises exception
        """
        try:
            params = {
                "account_number": account_number,
                "bank_code": bank_code
            }
            response = requests.get(
                f"{self.base_url}/bank/resolve",
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Account resolution failed: {e}")
            raise Exception(f"Account resolution failed: {str(e)}")
    
    def create_transfer_recipient(
        self, 
        name: str, 
        account_number: str, 
        bank_code: str
    ) -> Dict:
        """
        Create transfer recipient for payments
        
        Args:
            name: Recipient name
            account_number: Bank account number
            bank_code: Nigerian bank code
            
        Returns:
            Dict: Recipient information or raises exception
        """
        try:
            data = {
                "type": "nuban",
                "name": name,
                "account_number": account_number,
                "bank_code": bank_code
            }
            response = requests.post(
                f"{self.base_url}/transferrecipient",
                headers=self.headers,
                json=data,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Transfer recipient creation failed: {e}")
            raise Exception(f"Transfer recipient creation failed: {str(e)}")
    
    def initiate_transfer(
        self, 
        recipient: str, 
        amount_kobo: int, 
        reason: str
    ) -> Dict:
        """
        Initiate money transfer
        
        Args:
            recipient: Recipient code
            amount_kobo: Amount in kobo (Naira * 100)
            reason: Transfer reason
            
        Returns:
            Dict: Transfer information or raises exception
        """
        try:
            data = {
                "source": "balance",
                "amount": amount_kobo,
                "recipient": recipient,
                "reason": reason
            }
            response = requests.post(
                f"{self.base_url}/transfer",
                headers=self.headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Transfer initiation failed: {e}")
            raise Exception(f"Transfer initiation failed: {str(e)}")
    
    def verify_transfer(self, reference: str) -> Dict:
        """
        Verify transfer status
        
        Args:
            reference: Transfer reference
            
        Returns:
            Dict: Transfer verification details
        """
        try:
            response = requests.get(
                f"{self.base_url}/transfer/{reference}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Transfer verification failed: {e}")
            raise Exception(f"Transfer verification failed: {str(e)}")
    
    def get_banks(self) -> Dict:
        """
        Get list of supported banks
        
        Returns:
            Dict: List of banks
        """
        try:
            response = requests.get(
                f"{self.base_url}/bank",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Bank list retrieval failed: {e}")
            raise Exception(f"Bank list retrieval failed: {str(e)}")
    
    def process_worker_payment(
        self, 
        worker_name: str, 
        account_number: str, 
        bank_code: str, 
        amount: float,
        reason: str = "Salary payment"
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Complete payment processing for a worker
        
        Args:
            worker_name: Worker's full name
            account_number: Bank account number
            bank_code: Nigerian bank code
            amount: Payment amount in Naira
            reason: Payment reason
            
        Returns:
            Tuple[bool, str, Optional[str]]: (success, message, reference)
        """
        try:
            # Step 1: Create transfer recipient
            recipient_data = self.create_transfer_recipient(
                name=worker_name,
                account_number=account_number,
                bank_code=bank_code
            )
            
            if not recipient_data.get("status"):
                return False, "Failed to create transfer recipient", None
            
            recipient_code = recipient_data["data"]["recipient_code"]
            
            # Step 2: Initiate transfer (amount in kobo)
            amount_kobo = int(amount * 100)
            transfer_data = self.initiate_transfer(
                recipient=recipient_code,
                amount_kobo=amount_kobo,
                reason=reason
            )
            
            if not transfer_data.get("status"):
                return False, "Failed to initiate transfer", None
            
            reference = transfer_data["data"]["reference"]
            return True, "Payment processed successfully", reference
            
        except Exception as e:
            logger.error(f"Payment processing failed for {worker_name}: {e}")
            return False, str(e), None
    
    def validate_account_details(
        self, 
        account_number: str, 
        bank_code: str
    ) -> Tuple[bool, str]:
        """
        Validate bank account details before payment
        
        Args:
            account_number: Bank account number
            bank_code: Nigerian bank code
            
        Returns:
            Tuple[bool, str]: (is_valid, account_name)
        """
        try:
            account_data = self.resolve_account(account_number, bank_code)
            
            if account_data.get("status"):
                account_name = account_data["data"]["account_name"]
                return True, account_name
            else:
                return False, "Account resolution failed"
                
        except Exception as e:
            logger.error(f"Account validation failed: {e}")
            return False, str(e)
    
    def get_transaction_fee(self, amount: float) -> float:
        """
        Calculate Paystack transaction fee
        
        Args:
            amount: Transaction amount in Naira
            
        Returns:
            float: Transaction fee in Naira
        """
        # Paystack fees (as of 2024):
        # Transfers: ₦10 for amounts below ₦5,000
        # ₦25 for amounts ₦5,000 - ₦50,000
        # ₦50 for amounts above ₦50,000
        
        if amount < 5000:
            return 10.0
        elif amount <= 50000:
            return 25.0
        else:
            return 50.0
    
    def calculate_net_amount(self, gross_amount: float) -> Tuple[float, float]:
        """
        Calculate net amount after fees
        
        Args:
            gross_amount: Gross amount in Naira
            
        Returns:
            Tuple[float, float]: (net_amount, fee_amount)
        """
        fee = self.get_transaction_fee(gross_amount)
        net_amount = gross_amount - fee
        return net_amount, fee


# Global Paystack service instance
paystack_service = PaystackService()
