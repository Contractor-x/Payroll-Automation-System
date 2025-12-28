from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict
import logging

from backend.database import get_db, Worker, PaymentHistory, AuditLog
from backend.services.paystack import paystack_service
from backend.Config import settings

logger = logging.getLogger(__name__)


class PaymentScheduler:
    """
    Automated payment scheduling service
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    def start(self):
        """Start the payment scheduler"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("✅ Payment scheduler started")
    
    def stop(self):
        """Stop the payment scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("⏹️ Payment scheduler stopped")
    
    def schedule_daily_payment_check(self, hour: int = 9):
        """
        Schedule daily payment check at specified hour
        
        Args:
            hour: Hour of day to run (24-hour format)
        """
        trigger = CronTrigger(hour=hour, minute=0)
        self.scheduler.add_job(
            self.check_pending_payments,
            trigger,
            id="daily_payment_check",
            name="Daily Payment Check",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300  # 5 minutes grace period
        )
        logger.info(f"📅 Scheduled daily payment check at {hour}:00")
    
    def schedule_worker_payment(self, worker_id: int, payment_date: datetime):
        """
        Schedule a specific payment for a worker
        
        Args:
            worker_id: Worker ID
            payment_date: When to process the payment
        """
        trigger = DateTrigger(run_date=payment_date)
        job_id = f"worker_payment_{worker_id}_{payment_date.timestamp()}"
        
        self.scheduler.add_job(
            self.process_scheduled_payment,
            trigger,
            id=job_id,
            name=f"Payment for worker {worker_id}",
            args=[worker_id],
            max_instances=1
        )
        logger.info(f"💰 Scheduled payment for worker {worker_id} on {payment_date}")
    
    async def check_pending_payments(self):
        """
        Check for workers with payments due today
        This runs daily and identifies workers who need payment
        """
        logger.info("🔍 Checking for pending payments...")
        
        try:
            db = next(get_db())
            
            # Get workers with payments due today or overdue
            today = datetime.now().date()
            workers_due = db.query(Worker).filter(
                Worker.is_active == True,
                Worker.next_payment_date <= datetime.combine(today, datetime.max.time())
            ).all()
            
            pending_count = 0
            
            for worker in workers_due:
                # Check if there's already a pending payment for this worker today
                existing_payment = db.query(PaymentHistory).filter(
                    PaymentHistory.worker_id == worker.id,
                    PaymentHistory.status == "pending",
                    PaymentHistory.created_at >= datetime.combine(today, datetime.min.time())
                ).first()
                
                if not existing_payment:
                    # Create pending payment record
                    payment_record = PaymentHistory(
                        worker_id=worker.id,
                        amount=worker.salary_amount,
                        status="pending",
                        created_at=datetime.utcnow()
                    )
                    db.add(payment_record)
                    pending_count += 1
                    logger.info(f"📋 Created pending payment for {worker.name}: ₦{worker.salary_amount}")
            
            db.commit()
            
            if pending_count > 0:
                logger.info(f"✅ Found {pending_count} workers with payments due")
            else:
                logger.info("ℹ️ No new payments due today")
                
        except Exception as e:
            logger.error(f"❌ Error checking pending payments: {e}")
        finally:
            db.close()
    
    async def process_scheduled_payment(self, worker_id: int):
        """
        Process a scheduled payment for a worker
        
        Args:
            worker_id: Worker ID
        """
        logger.info(f"💳 Processing scheduled payment for worker {worker_id}")
        
        try:
            db = next(get_db())
            
            # Get worker
            worker = db.query(Worker).filter(Worker.id == worker_id).first()
            if not worker:
                logger.error(f"❌ Worker {worker_id} not found")
                return
            
            if not worker.is_active:
                logger.warning(f"⚠️ Worker {worker_id} is not active, skipping payment")
                return
            
            # Create payment record
            payment_record = PaymentHistory(
                worker_id=worker.id,
                amount=worker.salary_amount,
                status="pending",
                created_at=datetime.utcnow()
            )
            db.add(payment_record)
            db.commit()
            db.refresh(payment_record)
            
            # Process payment via Paystack
            success, message, reference = paystack_service.process_worker_payment(
                worker_name=worker.name,
                account_number=worker.account_number,
                bank_code=worker.bank_code,
                amount=float(worker.salary_amount),
                reason=f"Automated salary payment for {worker.name}"
            )
            
            if success:
                # Update payment record
                payment_record.status = "success"
                payment_record.transaction_reference = reference
                payment_record.paid_at = datetime.utcnow()
                
                # Update worker
                worker.last_paid = datetime.utcnow()
                worker.next_payment_date = self.calculate_next_payment_date(
                    worker.payment_frequency
                )
                
                logger.info(f"✅ Payment successful for {worker.name}: {reference}")
            else:
                # Payment failed
                payment_record.status = "failed"
                logger.error(f"❌ Payment failed for {worker.name}: {message}")
            
            db.commit()
            
            # Create audit log
            audit_log = AuditLog(
                user_id=0,  # System user
                action="scheduled_payment_processed",
                details=f"Scheduled payment for {worker.name}: {'Success' if success else 'Failed'} - {message}"
            )
            db.add(audit_log)
            db.commit()
            
        except Exception as e:
            logger.error(f"❌ Error processing scheduled payment for worker {worker_id}: {e}")
        finally:
            db.close()
    
    def calculate_next_payment_date(self, payment_frequency: str) -> datetime:
        """
        Calculate next payment date based on frequency
        
        Args:
            payment_frequency: weekly, bi-weekly, or monthly
            
        Returns:
            datetime: Next payment date
        """
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
    
    def get_scheduled_jobs(self) -> List[Dict]:
        """
        Get list of all scheduled jobs
        
        Returns:
            List[Dict]: List of job information
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time,
                "trigger": str(job.trigger)
            })
        return jobs
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a scheduled job
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            bool: True if job was cancelled, False if not found
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"🗑️ Cancelled job: {job_id}")
            return True
        except Exception:
            logger.warning(f"⚠️ Job not found: {job_id}")
            return False
    
    def reschedule_worker_payments(self):
        """
        Reschedule all worker payments based on their payment frequency
        This is useful when the system restarts
        """
        logger.info("🔄 Rescheduling all worker payments...")
        
        try:
            db = next(get_db())
            
            # Get all active workers
            workers = db.query(Worker).filter(Worker.is_active == True).all()
            
            for worker in workers:
                if worker.next_payment_date and worker.next_payment_date > datetime.now():
                    self.schedule_worker_payment(worker.id, worker.next_payment_date)
                    logger.info(f"📅 Rescheduled payment for {worker.name} on {worker.next_payment_date}")
            
            logger.info(f"✅ Rescheduled payments for {len(workers)} workers")
            
        except Exception as e:
            logger.error(f"❌ Error rescheduling worker payments: {e}")
        finally:
            db.close()
    
    def get_payment_statistics(self) -> Dict:
        """
        Get payment scheduling statistics
        
        Returns:
            Dict: Payment statistics
        """
        try:
            db = next(get_db())
            
            # Get counts
            total_workers = db.query(Worker).filter(Worker.is_active == True).count()
            workers_due_today = db.query(Worker).filter(
                Worker.is_active == True,
                Worker.next_payment_date <= datetime.now()
            ).count()
            
            pending_payments = db.query(PaymentHistory).filter(
                PaymentHistory.status == "pending"
            ).count()
            
            recent_payments = db.query(PaymentHistory).filter(
                PaymentHistory.status == "success",
                PaymentHistory.paid_at >= datetime.now() - timedelta(days=30)
            ).count()
            
            return {
                "scheduler_running": self.is_running,
                "total_active_workers": total_workers,
                "workers_due_today": workers_due_today,
                "pending_payments": pending_payments,
                "successful_payments_last_30_days": recent_payments,
                "scheduled_jobs": len(self.scheduler.get_jobs())
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting payment statistics: {e}")
            return {"error": str(e)}
        finally:
            db.close()


# Global payment scheduler instance
payment_scheduler = PaymentScheduler()


def setup_scheduler():
    """Setup and start the payment scheduler"""
    try:
        payment_scheduler.start()
        
        if settings.auto_payment_enabled:
            payment_scheduler.schedule_daily_payment_check(settings.payment_schedule_hour)
            logger.info(f"✅ Auto-payments enabled, daily check at {settings.payment_schedule_hour}:00")
        else:
            logger.info("ℹ️ Auto-payments disabled")
            
    except Exception as e:
        logger.error(f"❌ Failed to setup scheduler: {e}")


def stop_scheduler():
    """Stop the payment scheduler"""
    payment_scheduler.stop()


# Scheduler job functions (these need to be module-level for APScheduler)
async def daily_payment_check_job():
    """Daily payment check job wrapper"""
    await payment_scheduler.check_pending_payments()


async def scheduled_payment_job(worker_id: int):
    """Scheduled payment job wrapper"""
    await payment_scheduler.process_scheduled_payment(worker_id)
