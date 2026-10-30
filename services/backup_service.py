"""
GRIDWISE AI - Database Backup & Restoration Service
Phase 10 Database Reliability & Disaster Recovery

Features:
- Point-in-time timestamped hot backups using SQLite backup API.
- Pre-restoration integrity checks (PRAGMA integrity_check).
- Automated backup rotation (preserves latest 10 backups).
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timezone
import shutil
import sqlite3
import logging

from database.database import get_db_path, create_connection

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = BASE_DIR / "database" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


class DatabaseBackupService:
    """Manages database backups, restorations, and integrity audits."""

    @classmethod
    def backup_database(cls, custom_dir: Optional[Path] = None, tag: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a consistent online backup using SQLite's native backup API.
        Does not lock write transactions or corrupt concurrent operations.
        """
        dest_dir = custom_dir or BACKUP_DIR
        dest_dir.mkdir(parents=True, exist_ok=True)

        source_path = Path(db_path) if db_path else Path(get_db_path())
        if str(source_path) == ":memory:":
            raise ValueError("In-memory database cannot be backed up to disk.")

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        tag_suffix = f"_{tag}" if tag else ""
        backup_filename = f"gridwise_backup_{timestamp_str}{tag_suffix}.db"
        backup_path = dest_dir / backup_filename

        source_conn = create_connection(str(source_path))
        dest_conn = sqlite3.connect(str(backup_path))

        try:
            with dest_conn:
                source_conn.backup(dest_conn, pages=100)
            logger.info(f"Database backup created successfully: {backup_path}")
        finally:
            dest_conn.close()
            source_conn.close()

        # Check integrity of created backup
        is_healthy = cls.verify_backup_integrity(backup_path)

        # Rotate old backups (keep latest 10)
        cls._rotate_backups(dest_dir, keep=10)

        return {
            "status": "success" if is_healthy else "failed",
            "success": is_healthy,
            "filename": backup_filename,
            "backup_filename": backup_filename,
            "backup_path": str(backup_path),
            "size_bytes": backup_path.stat().st_size,
            "size_kb": round(backup_path.stat().st_size / 1024, 1),
            "integrity": "PASSED" if is_healthy else "CORRUPTED",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def verify_backup_integrity(cls, backup_path: Path) -> bool:
        """Runs PRAGMA integrity_check on a backup database file."""
        if not backup_path.exists():
            return False
        try:
            conn = sqlite3.connect(str(backup_path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            row = cursor.fetchone()
            conn.close()
            return bool(row and row[0] == "ok")
        except Exception as e:
            logger.error(f"Backup integrity check error: {e}")
            return False

    @classmethod
    def restore_database(cls, backup_path: Path) -> Dict[str, Any]:
        """Restores database from a verified healthy backup file."""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found at {backup_path}")

        if not cls.verify_backup_integrity(backup_path):
            raise ValueError("Restoration aborted: target backup failed PRAGMA integrity check.")

        target_path = Path(get_db_path())
        # Create a safety copy of current DB before replacement
        if target_path.exists():
            safety_copy = target_path.with_suffix(".pre_restore.bak")
            shutil.copy2(target_path, safety_copy)

        shutil.copy2(backup_path, target_path)
        logger.info(f"Database successfully restored from {backup_path}")

        return {
            "success": True,
            "restored_from": str(backup_path),
            "target_path": str(target_path),
            "restored_at": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def list_backups(cls, custom_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
        """Lists available backup files sorted newest first."""
        target_dir = custom_dir or BACKUP_DIR
        backups = []
        for p in sorted(target_dir.glob("*.db"), key=lambda x: x.stat().st_mtime, reverse=True):
            backups.append({
                "filename": p.name,
                "path": str(p),
                "size_bytes": p.stat().st_size,
                "size_kb": round(p.stat().st_size / 1024, 1),
                "modified_at": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(),
            })
        return backups

    @classmethod
    def _rotate_backups(cls, backup_dir: Path, keep: int = 10) -> None:
        """Removes backups older than the latest 'keep' files."""
        all_backups = sorted(backup_dir.glob("*.db"), key=lambda x: x.stat().st_mtime, reverse=True)
        if len(all_backups) > keep:
            for old_p in all_backups[keep:]:
                try:
                    old_p.unlink()
                    logger.info(f"Rotated old backup file: {old_p.name}")
                except Exception:
                    pass

# Aliases for convenient importing
BackupService = DatabaseBackupService
backup_service = DatabaseBackupService
