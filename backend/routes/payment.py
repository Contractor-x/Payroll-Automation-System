from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel
import requests
import json

from backend.database import get_db, Worker, PaymentHistory, AuditLog
from backend.auth.middleware import get_current_user
from backend.Config import settings

router = APIRouter()


# Pydantic models
class PaymentProcessRequest(BaseModel):
    worker_id: int
    amount: Optional[float] = None  # If None, use worker's salary


class PaymentHistoryResponse(BaseModel):
    id: int
    worker_id: int
    worker_name: str
    amount: float
    status: str
    transaction_reference: Optional[str]
    paystack_reference: Optional[str]
    paid_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class BalanceResponse(BaseModel):
    balance: float
    currency: str = "NGN"
    last_updated: datetime


class PendingPayment(BaseModel):
    id: int
    worker_id: int
    worker_name: str
    amount: float
    due_date: datetime
    status: str


class PaymentStats(BaseModel):
    total_workers: int
    active_workers: int
    monthly_cost: float
    pending_payments: int
    last_payment_date: Optional[datetime]


class PaystackBalance:
    """Paystack API client for balance and transfers"""
    
    def __init__(self):
        self.base_url = settings.paystack_base_url
        self.secret_key = settings.paystack_secret_key
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    def get_balance(self) -> dict:
        """Get Paystack account balance"""
        try:
            response = requests.get(
                f"{self.base_url}/balance",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Paystack API error: {str(e)}"
            )
    
    def resolve_account(self, account_number: str, bank_code: str) -> dict:
        """Resolve bank account details"""
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
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Account resolution failed: {str(e)}"
            )
    
    def create_transfer_recipient(self, name: str, account_number: str, bank_code: str) -> dict:
        """Create transfer recipient"""
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
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Transfer recipient creation failed: {str(e)}"
            )
    
    def initiate_transfer(self, recipient: str, amount: int, reason: str) -> dict:
        """Initiate money transfer"""
        try:
            data = {
                "source": "balance",
                "amount": amount,
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
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Transfer initiation failed: {str(e)}"
            )


def create_audit_log(db: Session, user_id: int, action: str, details: str, ip_address: str = None):
    """Create audit log entry"""
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip_address
    )
    db.add(audit_log)
    db.commit()


@router.get("/balance", response_model=BalanceResponse)
async def get_paystack_balance(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get current Paystack account balance
    """
    try:
        paystack = PaystackBalance()
        balance_data = paystack.get_balance()
        
        if balance_data.get("status") and balance_data.get("data"):
            balance_info = balance_data["data"][0]  # Get first balance entry
            
            balance_response = BalanceResponse(
                balance=float(balance_info["balance"]) / 100,  # Convert from kobo
                currency=balance_info.get("currency", "NGN"),
                last_updated=datetime.now()
            )
            
            # Create audit log
            create_audit_log(
                db, current_user.id, "balance_check",
                f"Checked balance: {balance_response.balance} {balance_response.currency}"
            )
            
            return balance_response
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to retrieve balance from Paystack"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving balance: {str(e)}"
        )


@router.post("/process", response_model=PaymentHistoryResponse)
async def process_payment(
    payment_request: PaymentProcessRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Process a payment to a worker
    """
    # Get worker
    worker = db.query(Worker).filter(Worker.id == payment_request.worker_id).first()
    
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
    
    if not worker.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Worker is not active"
        )
    
    # Determine amount (use provided amount or worker's salary)
    amount = payment_request.amount or float(worker.salary_amount)
    
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive"
        )
    
    # Check Paystack balance first
    try:
        paystack = PaystackBalance()
        balance_data = paystack.get_balance()
        
        if balance_data.get("status") and balance_data.get("data"):
            available_balance = float(balance_data["data"][0]["balance"]) / 100
            required_amount = amount
            
            if available_balance < required_amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient balance. Available: {available_balance:.2f}, Required: {required_amount:.2f}"
                )
    except HTTPException:
        raise
    except Exception:
        # Continue anyway, Paystack will handle insufficient funds
        pass
    
    # Create payment record
    payment_record = PaymentHistory(
        worker_id=worker.id,
        amount=amount,
        status="pending",
        approved_by=current_user.id
    )
    
    db.add(payment_record)
    db.commit()
    db.refresh(payment_record)
    
    try:
        # Process payment via Paystack
        paystack = PaystackBalance()
        
        # Step 1: Create transfer recipient
        recipient_data = paystack.create_transfer_recipient(
            name=worker.name,
            account_number=worker.account_number,
            bank_code=worker.bank_code
        )
        
        if not recipient_data.get("status"):
            raise Exception("Failed to create transfer recipient")
        
        recipient_code = recipient_data["data"]["recipient_code"]
        
        # Step 2: Initiate transfer (amount in kobo)
        amount_kobo = int(amount * 100)
        transfer_data = paystack.initiate_transfer(
            recipient=recipient_code,
            amount=amount_kobo,
            reason=f"Salary payment for {worker.name}"
        )
        
        if not transfer_data.get("status"):
            raise Exception("Failed to initiate transfer")
        
        # Update payment record with Paystack reference
        payment_record.status = "success"
        payment_record.transaction_reference = transfer_data["data"]["reference"]
        payment_record.paystack_reference = transfer_data["data"]["transfer_code"]
        payment_record.paid_at = datetime.utcnow()
        
        # Update worker last paid date
        worker.last_paid = datetime.utcnow()
        
        # Calculate next payment date
        worker.next_payment_date = calculate_next_payment_date(worker.payment_frequency)
        
        db.commit()
        
        # Create audit log
        create_audit_log(
            db, current_user.id, "payment_processed",
            f"Processed payment of {amount:.2f} to {worker.name} (Ref: {transfer_data['data']['reference']})"
        )
        
        return PaymentHistoryResponse(
            id=payment_record.id,
            worker_id=worker.id,
            worker_name=worker.name,
            amount=amount,
            status=payment_record.status,
            transaction_reference=payment_record.transaction_reference,
            paystack_reference=payment_record.paystack_reference,
            paid_at=payment_record.paid_at,
            created_at=payment_record.created_at
        )
        
    except HTTPException:
        # Update payment status to failed
        payment_record.status = "failed"
        db.commit()
        raise
    except Exception as e:
        # Update payment status to failed
        payment_record.status = "failed"
        db.commit()
        
        # Create audit log
        create_audit_log(
            db, current_user.id, "payment_failed",
            f"Payment failed for {worker.name}: {str(e)}"
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment processing failed: {str(e)}"
        )


@router.get("/history", response_model=List[PaymentHistoryResponse])
async def get_payment_history(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    worker_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get payment history with optional filtering
    """
    query = db.query(PaymentHistory).join(Worker)
    
    # Apply filters
    if status_filter:
        query = query.filter(PaymentHistory.status == status_filter)
    
    if worker_id:
        query = query.filter(PaymentHistory.worker_id == worker_id)
    
    if start_date:
        query = query.filter(PaymentHistory.created_at >= start_date)
    
    if end_date:
        query = query.filter(PaymentHistory.created_at <= end_date)
    
    # Order by creation date (newest first)
    query = query.order_by(desc(PaymentHistory.created_at))
    
    # Apply pagination
    payments = query.offset(skip).limit(limit).all()
    
    # Convert to response model
    payment_responses = []
    for payment in payments:
        payment_response = PaymentHistoryResponse(
            id=payment.id,
            worker_id=payment.worker_id,
            worker_name=payment.worker.name,
            amount=float(payment.amount),
            status=payment.status,
            transaction_reference=payment.transaction_reference,
            paystack_reference=payment.paystack_reference,
            paid_at=payment.paid_at,
            created_at=payment.created_at
        )
        payment_responses.append(payment_response)
    
    return payment_responses


@router.get("/stats", response_model=PaymentStats)
async def get_payment_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get payment statistics and dashboard data
    """
    # Get worker statistics
    total_workers = db.query(Worker).count()
    active_workers = db.query(Worker).filter(Worker.is_active == True).count()
    
    # Calculate monthly cost
    workers = db.query(Worker).filter(Worker.is_active == True).all()
    monthly_cost = 0
    
    for worker in workers:
        salary = float(worker.salary_amount)
        if worker.payment_frequency == "monthly":
            monthly_cost += salary
        elif worker.payment_frequency == "bi-weekly":
            monthly_cost += salary * 2
        elif worker.payment_frequency == "weekly":
            monthly_cost += salary * 4
    
    # Get pending payments
    pending_payments = db.query(PaymentHistory).filter(
        PaymentHistory.status == "pending"
    ).count()
    
    # Get last payment date
    last_payment = db.query(PaymentHistory).filter(
        PaymentHistory.status == "success"
    ).order_by(desc(PaymentHistory.paid_at)).first()
    
    last_payment_date = last_payment.paid_at if last_payment else None
    
    return PaymentStats(
        total_workers=total_workers,
        active_workers=active_workers,
        monthly_cost=monthly_cost,
        pending_payments=pending_payments,
        last_payment_date=last_payment_date
    )


@router.get("/pending", response_model=List[PendingPayment])
async def get_pending_payments(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get pending payments that need approval
    """
    # This could be implemented to show payments scheduled for today
    # that need manual approval before processing
    workers_due = db.query(Worker).filter(
        and_(
            Worker.is_active == True,
            Worker.next_payment_date <= datetime.utcnow()
        )
    ).all()
    
    pending_list = []
    for worker in workers_due:
        pending_payment = PendingPayment(
            id=0,  # This would be a scheduled payment ID
            worker_id=worker.id,
            worker_name=worker.name,
            amount=float(worker.salary_amount),
            due_date=worker.next_payment_date,
            status="pending_approval"
        )
        pending_list.append(pending_payment)
    
    return pending_list


def calculate_next_payment_date(payment_frequency: str) -> datetime:
    """Calculate next payment date"""
    from datetime import timedelta
    
    today = datetime.now().date()
    
    if payment_frequency == "weekly":
        next_date = today + timedelta(weeks=1)
    elif payment_frequency == "bi-weekly":
        next_date = today + timedelta(weeks=2)
    else:  # monthly
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        
        try:
            next_date = next_month.replace(day=today.day)
        except ValueError:
            if next_month.month == 12:
                next_date = next_month.replace(year=next_month.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                next_date = next_month.replace(month=next_month.month + 1, day=1) - timedelta(days=1)
    
    return datetime.combine(next_date, datetime.min.time())


# Import get_current_user at the end to avoid circular import
from backend.auth.middleware import get_current_user
