#!/usr/bin/env python3
"""
Database initialization script for Payroll Automation System
Creates all tables and sets up the database
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.database import init_db, create_tables, drop_tables, SessionLocal, engine
from backend.Config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize the database"""
    logger.info("🚀 Starting database initialization...")
    logger.info(f"Database URL: {settings.database_url}")
    
    try:
        # Create database directory if it doesn't exist
        if settings.database_url.startswith("sqlite"):
            db_path = settings.database_url.replace("sqlite:///", "")
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"📁 Created database directory: {db_dir}")
        
        # Initialize database tables
        logger.info("📋 Creating database tables...")
        init_db()
        
        # Verify tables were created
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
            
        expected_tables = ['users', 'workers', 'payment_history', 'audit_logs']
        missing_tables = [table for table in expected_tables if table not in tables]
        
        if missing_tables:
            logger.error(f"❌ Missing tables: {missing_tables}")
            return False
        
        logger.info("✅ All database tables created successfully!")
        logger.info(f"📊 Tables created: {', '.join(tables)}")
        
        # Test database connection
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            logger.info("✅ Database connection test passed")
        finally:
            db.close()
        
        logger.info("🎉 Database initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False


def reset_database():
    """Drop and recreate all tables (WARNING: This will delete all data!)"""
    logger.warning("⚠️  WARNING: This will delete ALL data in the database!")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() != 'yes':
        logger.info("❌ Database reset cancelled")
        return False
    
    try:
        logger.info("🗑️ Dropping all tables...")
        drop_tables()
        
        logger.info("📋 Recreating tables...")
        create_tables()
        
        logger.info("✅ Database reset completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        return False


def check_database_status():
    """Check current database status"""
    logger.info("🔍 Checking database status...")
    
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # Check tables
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
            
            # Check table counts
            table_counts = {}
            for table in tables:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.fetchone()[0]
                table_counts[table] = count
            
            logger.info("📊 Database Status:")
            logger.info(f"  Tables: {len(tables)}")
            for table, count in table_counts.items():
                logger.info(f"    {table}: {count} records")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Database status check failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Payroll System Database Management")
    parser.add_argument("action", choices=["init", "reset", "status"], 
                       help="Action to perform")
    
    args = parser.parse_args()
    
    if args.action == "init":
        success = main()
        sys.exit(0 if success else 1)
    elif args.action == "reset":
        success = reset_database()
        sys.exit(0 if success else 1)
    elif args.action == "status":
        success = check_database_status()
        sys.exit(0 if success else 1)
