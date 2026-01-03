#!/usr/bin/env python3
"""
Database migration script to add lockout_until column to users table
Run this script to update existing databases
"""

import sys
import sqlite3
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.Config import settings


def migrate_lockout_column():
    """Add lockout_until column to users table"""
    
    # Get database path from URL
    db_url = settings.database_url
    if "sqlite:///" in db_url:
        db_path = db_url.replace("sqlite:///", "")
    else:
        print("❌ Migration only supports SQLite databases")
        return False
    
    db_file = Path(db_path)
    if not db_file.exists():
        print(f"❌ Database file not found: {db_path}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'lockout_until' in columns:
            print("✅ lockout_until column already exists")
            conn.close()
            return True
        
        # Add the column
        print("🔧 Adding lockout_until column to users table...")
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN lockout_until DATETIME NULL
        """)
        
        conn.commit()
        conn.close()
        
        print("✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False


if __name__ == "__main__":
    print("🔄 Running database migration for 5-second lockout...")
    
    success = migrate_lockout_column()
    
    if success:
        print("✅ Database is ready for 5-second lockout feature!")
    else:
        print("❌ Migration failed. Please check the error above.")
        sys.exit(1)
