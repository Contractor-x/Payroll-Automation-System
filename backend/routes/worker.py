from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, EmailStr, validator

from backend.database import get_db, Worker, PaymentHistory, AuditLog, NIGERIAN_BANK_CODES
from backend.auth.middleware import get_current_user

router = APIRouter()


# Pydantic models for request/response
class WorkerBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    bank_name: str
    account_number: str
    bank_code: str
    salary_amount: float
    payment_frequency: str = "monthly"
    
    @validator('bank_code')
    def validate_bank_code(cls, v):
        if v not in NIGERIAN_BANK_CODES:
            raise ValueError(f'Invalid bank code. Must be one of: {", ".join(NIGERIAN_BANK_CODES.keys())}')
        return v
    
    @validator('payment_frequency')
    def validate_payment_frequency(cls, v):
        valid_frequencies = ['weekly', 'bi-weekly', 'monthly']
        if v not in valid_frequencies:
            raise ValueError(f'Payment frequency must be one of: {", ".join(valid_frequencies)}')
        return v
    
    @validator('salary_amount')
    def validate_salary_amount(cls, v):
        if v <= 0:
            raise ValueError('Salary amount must be positive')
        if v > 10000000:  # 10 million Naira maximum
            raise ValueError('Salary amount cannot exceed 10,000,000 Naira')
        return v


class WorkerCreate(WorkerBase):
    pass


class WorkerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    bank_code: Optional[str] = None
    salary_amount: Optional[float] = None
    payment_frequency: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('bank_code')
    def validate_bank_code(cls, v):
        if v is not None and v not in NIGERIAN_BANK_CODES:
            raise ValueError(f'Invalid bank code. Must be one of: {", ".join(NIGERIAN_BANK_CODES.keys())}')
        return v
    
    @validator('payment_frequency')
    def validate_payment_frequency(cls, v):
        if v is not None:
            valid_frequencies = ['weekly', 'bi-weekly', 'monthly']
            if v not in valid_frequencies:
                raise ValueError(f'Payment frequency must be one of: {", ".join(valid_frequencies)}')
        return v
    
    @validator('salary_amount')
    def validate_salary_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Salary amount must be positive')
        if v is not None and v > 10000000:
            raise ValueError('Salary amount cannot exceed 10,000,000 Naira')
        return v


class WorkerResponse(BaseModel):
    id: int
    name: str
    email: Optional[str]
    bank_name: str
    account_number: str
    bank_code: str
    salary_amount: float
    payment_frequency: str
    last_paid: Optional[datetime]
    next_payment_date: Optional[datetime]
    is_active: bool
    created_at: datetime
    bank_display_name: str
    
    class Config:
        from_attributes = True


class WorkerListResponse(BaseModel):
    workers: List[WorkerResponse]
    total: int
    active_count: int
    total_monthly_cost: float


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


@router.get("/", response_model=WorkerListResponse)
async def get_workers(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get all workers with optional filtering and search
    """
    query = db.query(Worker)
    
    # Filter by active status if requested
    if active_only:
        query = query.filter(Worker.is_active == True)
    
    # Search functionality
    if search:
        search_filter = or_(
            Worker.name.contains(search),
            Worker.email.contains(search),
            Worker.bank_name.contains(search),
            Worker.account_number.contains(search)
        )
        query = query.filter(search_filter)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination
    workers = query.offset(skip).limit(limit).all()
    
    # Add bank display names
    worker_responses = []
    active_count = 0
    total_monthly_cost = 0
    
    for worker in workers:
        worker_data = WorkerResponse(
            id=worker.id,
            name=worker.name,
            email=worker.email,
            bank_name=worker.bank_name,
            account_number=worker.account_number,
            bank_code=worker.bank_code,
            salary_amount=float(worker.salary_amount),
            payment_frequency=worker.payment_frequency,
            last_paid=worker.last_paid,
            next_payment_date=worker.next_payment_date,
            is_active=worker.is_active,
            created_at=worker.created_at,
            bank_display_name=NIGERIAN_BANK_CODES.get(worker.bank_code, worker.bank_name)
        )
        worker_responses.append(worker_data)
        
        if worker.is_active:
            active_count += 1
            # Calculate monthly cost based on payment frequency
            if worker.payment_frequency == 'monthly':
                total_monthly_cost += float(worker.salary_amount)
            elif worker.payment_frequency == 'bi-weekly':
                total_monthly_cost += float(worker.salary_amount) * 2
            elif worker.payment_frequency == 'weekly':
                total_monthly_cost += float(worker.salary_amount) * 4
    
    return WorkerListResponse(
        workers=worker_responses,
        total=total,
        active_count=active_count,
        total_monthly_cost=total_monthly_cost
    )


@router.get("/{worker_id}", response_model=WorkerResponse)
async def get_worker(
    worker_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get a specific worker by ID
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
    
    return WorkerResponse(
        id=worker.id,
        name=worker.name,
        email=worker.email,
        bank_name=worker.bank_name,
        account_number=worker.account_number,
        bank_code=worker.bank_code,
        salary_amount=float(worker.salary_amount),
        payment_frequency=worker.payment_frequency,
        last_paid=worker.last_paid,
        next_payment_date=worker.next_payment_date,
        is_active=worker.is_active,
        created_at=worker.created_at,
        bank_display_name=NIGERIAN_BANK_CODES.get(worker.bank_code, worker.bank_name)
    )


@router.post("/", response_model=WorkerResponse)
async def create_worker(
    worker_data: WorkerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Create a new worker
    """
    # Check if email already exists (if provided)
    if worker_data.email:
        existing_worker = db.query(Worker).filter(Worker.email == worker_data.email).first()
        if existing_worker:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Worker with this email already exists"
            )
    
    # Calculate next payment date
    next_payment_date = calculate_next_payment_date(worker_data.payment_frequency)
    
    # Create worker
    db_worker = Worker(
        name=worker_data.name,
        email=worker_data.email,
        bank_name=worker_data.bank_name,
        account_number=worker_data.account_number,
        bank_code=worker_data.bank_code,
        salary_amount=worker_data.salary_amount,
        payment_frequency=worker_data.payment_frequency,
        next_payment_date=next_payment_date,
        is_active=True
    )
    
    db.add(db_worker)
    db.commit()
    db.refresh(db_worker)
    
    # Create audit log
    create_audit_log(
        db, current_user.id, "worker_created",
        f"Created worker: {worker_data.name} (ID: {db_worker.id})"
    )
    
    return WorkerResponse(
        id=db_worker.id,
        name=db_worker.name,
        email=db_worker.email,
        bank_name=db_worker.bank_name,
        account_number=db_worker.account_number,
        bank_code=db_worker.bank_code,
        salary_amount=float(db_worker.salary_amount),
        payment_frequency=db_worker.payment_frequency,
        last_paid=db_worker.last_paid,
        next_payment_date=db_worker.next_payment_date,
        is_active=db_worker.is_active,
        created_at=db_worker.created_at,
        bank_display_name=NIGERIAN_BANK_CODES.get(db_worker.bank_code, db_worker.bank_name)
    )


@router.put("/{worker_id}", response_model=WorkerResponse)
async def update_worker(
    worker_id: int,
    worker_update: WorkerUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Update an existing worker
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
    
    # Store old values for audit log
    old_values = {
        'name': worker.name,
        'salary_amount': float(worker.salary_amount),
        'is_active': worker.is_active
    }
    
    # Update fields
    update_data = worker_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(worker, field, value)
    
    # If salary or payment frequency changed, recalculate next payment date
    if 'salary_amount' in update_data or 'payment_frequency' in update_data:
        worker.next_payment_date = calculate_next_payment_date(worker.payment_frequency)
    
    db.commit()
    db.refresh(worker)
    
    # Create audit log
    changes = []
    for field, new_value in update_data.items():
        old_value = old_values.get(field, getattr(worker, field))
        if field == 'salary_amount':
            old_value = float(old_value) if old_value else None
            new_value = float(new_value) if new_value else None
        changes.append(f"{field}: {old_value} -> {new_value}")
    
    audit_details = f"Updated worker {worker.name} (ID: {worker_id}): {', '.join(changes)}"
    create_audit_log(db, current_user.id, "worker_updated", audit_details)
    
    return WorkerResponse(
        id=worker.id,
        name=worker.name,
        email=worker.email,
        bank_name=worker.bank_name,
        account_number=worker.account_number,
        bank_code=worker.bank_code,
        salary_amount=float(worker.salary_amount),
        payment_frequency=worker.payment_frequency,
        last_paid=worker.last_paid,
        next_payment_date=worker.next_payment_date,
        is_active=worker.is_active,
        created_at=worker.created_at,
        bank_display_name=NIGERIAN_BANK_CODES.get(worker.bank_code, worker.bank_name)
    )


@router.delete("/{worker_id}")
async def delete_worker(
    worker_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Delete a worker (soft delete by setting is_active to False)
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
    
    # Soft delete
    worker.is_active = False
    db.commit()
    
    # Create audit log
    create_audit_log(
        db, current_user.id, "worker_deleted",
        f"Deactivated worker: {worker.name} (ID: {worker_id})"
    )
    
    return {"message": f"Worker {worker.name} has been deactivated"}


@router.get("/{worker_id}/payment-history")
async def get_worker_payment_history(
    worker_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get payment history for a specific worker
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
    
    payments = (db.query(PaymentHistory)
               .filter(PaymentHistory.worker_id == worker_id)
               .order_by(PaymentHistory.created_at.desc())
               .offset(skip)
               .limit(limit)
               .all())
    
    return {
        "worker_id": worker_id,
        "worker_name": worker.name,
        "payments": payments,
        "total_payments": len(payments)
    }


@router.get("/bank-codes/list")
async def get_bank_codes(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Get list of supported Nigerian bank codes
    """
    return {
        "bank_codes": NIGERIAN_BANK_CODES,
        "total_banks": len(NIGERIAN_BANK_CODES)
    }


def calculate_next_payment_date(payment_frequency: str) -> datetime:
    """
    Calculate next payment date based on frequency
    """
    from datetime import timedelta
    
    today = datetime.now().date()
    
    if payment_frequency == "weekly":
        next_date = today + timedelta(weeks=1)
    elif payment_frequency == "bi-weekly":
        next_date = today + timedelta(weeks=2)
    else:  # monthly
        # Add one month, handling month end cases
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        
        # Handle case where next month doesn't have the same day
        try:
            next_date = next_month.replace(day=today.day)
        except ValueError:
            # If day doesn't exist in next month, use last day of next month
            if next_month.month == 12:
                next_date = next_month.replace(year=next_month.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                next_date = next_month.replace(month=next_month.month + 1, day=1) - timedelta(days=1)
    
    return datetime.combine(next_date, datetime.min.time())


# Import get_current_user at the end to avoid circular import
from backend.auth.middleware import get_current_user
