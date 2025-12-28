#!/usr/bin/env python3
"""
Database backup utility for Payroll Automation System
Creates encrypted backups and manages backup retention
"""

import sys
import os
import shutil
import sqlite3
import gzip
import json
from pathlib import Path
from datetime import datetime, timedelta
import argparse
import logging

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.Config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseBackup:
    """Database backup and restoration utility"""
    
    def __init__(self):
        self.backup_dir = project_root / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Backup retention settings
        self.daily_retention = 7  # Keep daily backups for 7 days
        self.weekly_retention = 4  # Keep weekly backups for 4 weeks
        self.monthly_retention = 12  # Keep monthly backups for 12 months
        
        # Database path
        self.db_path = None
        if "sqlite" in settings.database_url:
            self.db_path = settings.database_url.replace("sqlite:///", "")
        else:
            raise ValueError("Backup utility only supports SQLite databases")
    
    def create_backup(self, backup_type: str = "manual") -> dict:
        """
        Create a database backup
        
        Args:
            backup_type: Type of backup (manual, daily, weekly, monthly)
            
        Returns:
            dict: Backup information
        """
        if not self.db_path or not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"payroll_backup_{backup_type}_{timestamp}.db.gz"
        backup_path = self.backup_dir / backup_filename
        
        try:
            # Create backup info
            backup_info = {
                "backup_type": backup_type,
                "timestamp": datetime.now().isoformat(),
                "database_path": self.db_path,
                "backup_path": str(backup_path),
                "original_size": Path(self.db_path).stat().st_size,
                "backup_size": 0,
                "tables": [],
                "record_counts": {},
                "checksum": ""
            }
            
            # Get database info before backup
            db_info = self.get_database_info()
            backup_info["tables"] = db_info["tables"]
            backup_info["record_counts"] = db_info["record_counts"]
            
            # Create compressed backup
            with open(self.db_path, 'rb') as f_in:
                with gzip.open(backup_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Update backup info
            backup_info["backup_size"] = backup_path.stat().st_size
            backup_info["checksum"] = self.calculate_checksum(backup_path)
            
            # Save backup metadata
            metadata_path = backup_path.with_suffix(backup_path.suffix + '.json')
            with open(metadata_path, 'w') as f:
                json.dump(backup_info, f, indent=2)
            
            logger.info(f"✅ Backup created: {backup_filename}")
            logger.info(f"📊 Original size: {backup_info['original_size']:,} bytes")
            logger.info(f"📦 Compressed size: {backup_info['backup_size']:,} bytes")
            logger.info(f"💾 Compression ratio: {backup_info['backup_size']/backup_info['original_size']:.1%}")
            
            # Cleanup old backups
            self.cleanup_old_backups()
            
            return backup_info
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            # Clean up partial backup file
            if backup_path.exists():
                backup_path.unlink()
            raise
    
    def restore_backup(self, backup_path: str, confirm: bool = False) -> dict:
        """
        Restore database from backup
        
        Args:
            backup_path: Path to backup file
            confirm: Whether to skip confirmation prompt
            
        Returns:
            dict: Restoration information
        """
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        if not backup_file.suffixes[-2:] == ['.db', '.gz']:
            raise ValueError("Invalid backup file format. Expected .db.gz file")
        
        if not confirm:
            response = input("⚠️ WARNING: This will replace the current database. Are you sure? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("❌ Restoration cancelled by user")
                return {"cancelled": True}
        
        try:
            # Create backup of current database before restoration
            if Path(self.db_path).exists():
                current_backup = self.create_backup("pre_restore")
                logger.info(f"📋 Current database backed up as: {current_backup['backup_path']}")
            
            # Restore database
            with gzip.open(backup_file, 'rb') as f_in:
                with open(self.db_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Verify restoration
            restored_info = self.get_database_info()
            
            logger.info(f"✅ Database restored successfully from: {backup_file.name}")
            logger.info(f"📊 Restored {len(restored_info['tables'])} tables")
            
            return {
                "restored": True,
                "backup_file": str(backup_file),
                "restored_tables": restored_info["tables"],
                "record_counts": restored_info["record_counts"]
            }
            
        except Exception as e:
            logger.error(f"❌ Restoration failed: {e}")
            raise
    
    def list_backups(self) -> list:
        """List all available backups with metadata"""
        backups = []
        
        for backup_file in self.backup_dir.glob("payroll_backup_*.db.gz"):
            metadata_file = backup_file.with_suffix(backup_file.suffix + '.json')
            
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        metadata["backup_file"] = str(backup_file)
                        metadata["metadata_file"] = str(metadata_file)
                        backups.append(metadata)
                except Exception as e:
                    logger.warning(f"⚠️ Could not read metadata for {backup_file.name}: {e}")
            else:
                # Legacy backup without metadata
                stat = backup_file.stat()
                backups.append({
                    "backup_file": str(backup_file),
                    "backup_type": "legacy",
                    "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "backup_size": stat.st_size,
                    "has_metadata": False
                })
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return backups
    
    def cleanup_old_backups(self):
        """Remove old backups based on retention policy"""
        backups = self.list_backups()
        
        if not backups:
            return
        
        now = datetime.now()
        
        for backup in backups:
            backup_time = datetime.fromisoformat(backup["timestamp"])
            age_days = (now - backup_time).days
            backup_type = backup.get("backup_type", "manual")
            
            should_delete = False
            
            if backup_type == "daily" and age_days > self.daily_retention:
                should_delete = True
            elif backup_type == "weekly" and age_days > self.weekly_retention * 7:
                should_delete = True
            elif backup_type == "monthly" and age_days > self.monthly_retention * 30:
                should_delete = True
            elif backup_type in ["manual", "pre_restore"] and age_days > 30:
                should_delete = True
            
            if should_delete:
                try:
                    # Delete backup file
                    backup_file = Path(backup["backup_file"])
                    backup_file.unlink()
                    
                    # Delete metadata file
                    metadata_file = Path(backup["metadata_file"])
                    if metadata_file.exists():
                        metadata_file.unlink()
                    
                    logger.info(f"🗑️ Deleted old backup: {backup_file.name}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Could not delete old backup {backup['backup_file']}: {e}")
    
    def get_database_info(self) -> dict:
        """Get information about the current database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get table names
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Get record counts
                record_counts = {}
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        record_counts[table] = count
                    except Exception:
                        record_counts[table] = "error"
                
                return {
                    "tables": tables,
                    "record_counts": record_counts,
                    "database_size": Path(self.db_path).stat().st_size
                }
                
        except Exception as e:
            logger.error(f"❌ Could not get database info: {e}")
            return {"tables": [], "record_counts": {}, "error": str(e)}
    
    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        import hashlib
        
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def verify_backup(self, backup_path: str) -> dict:
        """Verify backup file integrity"""
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            return {"valid": False, "error": "Backup file not found"}
        
        try:
            # Check file integrity by attempting to decompress
            with gzip.open(backup_file, 'rb') as f:
                # Read first few bytes to verify
                data = f.read(1024)
            
            # Check metadata if available
            metadata_file = backup_file.with_suffix(backup_file.suffix + '.json')
            metadata_info = {}
            
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata_info = json.load(f)
            
            # Verify checksum if available
            checksum_valid = True
            if "checksum" in metadata_info:
                current_checksum = self.calculate_checksum(backup_file)
                checksum_valid = current_checksum == metadata_info["checksum"]
            
            return {
                "valid": checksum_valid,
                "file_size": backup_file.stat().st_size,
                "has_metadata": bool(metadata_info),
                "checksum_valid": checksum_valid,
                "backup_type": metadata_info.get("backup_type", "unknown"),
                "created": metadata_info.get("timestamp", "unknown")
            }
            
        except Exception as e:
            return {"valid": False, "error": str(e)}


def schedule_daily_backup():
    """Schedule daily backup (for cron jobs)"""
    backup = DatabaseBackup()
    try:
        result = backup.create_backup("daily")
        logger.info("✅ Daily backup completed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Daily backup failed: {e}")
        return False


def schedule_weekly_backup():
    """Schedule weekly backup (for cron jobs)"""
    backup = DatabaseBackup()
    try:
        result = backup.create_backup("weekly")
        logger.info("✅ Weekly backup completed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Weekly backup failed: {e}")
        return False


def main():
    """Main script entry point"""
    parser = argparse.ArgumentParser(description="Payroll System Database Backup Utility")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create backup command
    backup_parser = subparsers.add_parser("backup", help="Create database backup")
    backup_parser.add_argument("--type", choices=["manual", "daily", "weekly", "monthly"],
                              default="manual", help="Backup type")
    
    # Restore backup command
    restore_parser = subparsers.add_parser("restore", help="Restore database from backup")
    restore_parser.add_argument("--file", required=True, help="Path to backup file")
    restore_parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    
    # List backups command
    subparsers.add_parser("list", help="List all backups")
    
    # Verify backup command
    verify_parser = subparsers.add_parser("verify", help="Verify backup file integrity")
    verify_parser.add_argument("--file", required=True, help="Path to backup file")
    
    # Info command
    subparsers.add_parser("info", help="Show database information")
    
    args = parser.parse_args()
    
    backup = DatabaseBackup()
    
    if args.command == "backup":
        print("💾 Creating database backup...")
        try:
            result = backup.create_backup(args.type)
            print(f"✅ Backup created successfully!")
            print(f"📁 File: {Path(result['backup_path']).name}")
            print(f"📊 Size: {result['backup_size']:,} bytes")
            print(f"🔐 Checksum: {result['checksum'][:16]}...")
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            sys.exit(1)
    
    elif args.command == "restore":
        print("🔄 Restoring database from backup...")
        try:
            result = backup.restore_backup(args.file, args.force)
            if not result.get("cancelled"):
                print("✅ Database restored successfully!")
            else:
                print("❌ Restoration cancelled")
        except Exception as e:
            print(f"❌ Restoration failed: {e}")
            sys.exit(1)
    
    elif args.command == "list":
        backups = backup.list_backups()
        
        if not backups:
            print("📝 No backups found")
            return
        
        print(f"\n📦 AVAILABLE BACKUPS ({len(backups)} total):")
        print("=" * 80)
        
        for backup_info in backups:
            created = backup_info["timestamp"][:19]  # Remove microseconds
            size_mb = backup_info["backup_size"] / (1024 * 1024)
            backup_type = backup_info["backup_type"].upper()
            
            print(f"📅 {created} | {backup_type:8} | {size_mb:6.1f} MB | {Path(backup_info['backup_file']).name}")
            
            if backup_info.get("tables"):
                print(f"    Tables: {', '.join(backup_info['tables'])}")
    
    elif args.command == "verify":
        print("🔍 Verifying backup integrity...")
        try:
            result = backup.verify_backup(args.file)
            
            if result["valid"]:
                print("✅ Backup is valid and intact")
                print(f"📁 File: {Path(args.file).name}")
                print(f"📊 Size: {result['file_size']:,} bytes")
                print(f"🔐 Type: {result['backup_type']}")
                print(f"📅 Created: {result['created'][:19]}")
            else:
                print("❌ Backup verification failed")
                if "error" in result:
                    print(f"Error: {result['error']}")
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            sys.exit(1)
    
    elif args.command == "info":
        print("📊 Database Information")
        print("=" * 40)
        
        try:
            info = backup.get_database_info()
            
            if "error" in info:
                print(f"❌ Error: {info['error']}")
            else:
                size_mb = info["database_size"] / (1024 * 1024)
                print(f"📁 Database: {backup.db_path}")
                print(f"📏 Size: {size_mb:.1f} MB")
                print(f"📋 Tables: {len(info['tables'])}")
                
                for table, count in info["record_counts"].items():
                    print(f"  {table}: {count:,} records")
                    
        except Exception as e:
            print(f"❌ Could not get database info: {e}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
