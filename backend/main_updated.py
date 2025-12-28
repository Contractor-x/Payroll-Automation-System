from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.Config import settings
from backend.auth.middleware import setup_middleware, lifespan
from backend.routes import auth, worker, payment
from backend.database import init_db
from backend.services.Payment_scheduler import setup_scheduler, payment_scheduler


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    # Create FastAPI app with custom lifespan
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Secure payroll automation system with Paystack integration",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan
    )
    
    # Setup middleware
    setup_middleware(app)
    
    # Include routers
    app.include_router(
        auth.router,
        prefix="/api/auth",
        tags=["Authentication"]
    )
    
    app.include_router(
        worker.router,
        prefix="/api/workers",
        tags=["Workers"]
    )
    
    app.include_router(
        payment.router,
        prefix="/api/payments",
        tags=["Payments"]
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "app_name": settings.app_name,
            "version": settings.app_version,
            "database": "connected",
            "scheduler_running": payment_scheduler.is_running,
            "timestamp": "2025-01-01T00:00:00Z"
        }
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with API information"""
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "docs": "/docs" if settings.debug else "disabled",
            "endpoints": {
                "auth": "/api/auth",
                "workers": "/api/workers", 
                "payments": "/api/payments"
            },
            "scheduler": {
                "running": payment_scheduler.is_running,
                "auto_payments": settings.auto_payment_enabled,
                "schedule_hour": settings.payment_schedule_hour
            }
        }
    
    # Scheduler endpoints
    @app.get("/api/scheduler/status")
    async def get_scheduler_status():
        """Get payment scheduler status"""
        return payment_scheduler.get_payment_statistics()
    
    @app.get("/api/scheduler/jobs")
    async def get_scheduled_jobs():
        """Get list of scheduled jobs"""
        return {"jobs": payment_scheduler.get_scheduled_jobs()}
    
    @app.post("/api/scheduler/reschedule")
    async def reschedule_worker_payments():
        """Reschedule all worker payments"""
        payment_scheduler.reschedule_worker_payments()
        return {"message": "Worker payments rescheduled"}
    
    # Initialize database on startup
    @app.on_event("startup")
    async def startup_event():
        """Initialize database and scheduler on startup"""
        try:
            init_db()
            print("✅ Database initialized successfully")
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
        
        # Setup and start scheduler
        try:
            setup_scheduler()
            print("✅ Payment scheduler initialized successfully")
        except Exception as e:
            print(f"❌ Scheduler initialization failed: {e}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        try:
            from backend.services.Payment_scheduler import stop_scheduler
            stop_scheduler()
            print("✅ Payment scheduler stopped")
        except Exception as e:
            print(f"⚠️ Error stopping scheduler: {e}")
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    # Run with uvicorn when script is executed directly
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )
