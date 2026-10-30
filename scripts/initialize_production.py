"""
GRIDWISE AI - Production Initialization Script
Initializes directories, SQLite database, seeds RBAC accounts, and creates baseline hot backup.
"""

import os
import sys

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import init_db, migrate_phase10_tables, check_db_health
from services.security_service import SecurityService
from services.backup_service import BackupService

def init_production():
    print("=" * 70)
    print("GRIDWISE AI - INITIALIZING PRODUCTION ENVIRONMENT")
    print("=" * 70)

    # 1. Ensure required directories
    required_dirs = [
        "database",
        "logs",
        "backups",
        "data/raw",
        "data/processed",
        "data/scenarios",
        "data/forecasts",
        "data/results",
        "reports"
    ]
    for d in required_dirs:
        os.makedirs(d, exist_ok=True)
        print(f"[*] Verified directory: {d}")

    # 2. Initialize / Verify SQLite database
    db_path = os.path.join("database", "gridwise.db")
    print(f"\n[*] Initializing / verifying database at: {db_path}")
    init_db(db_path)
    migrate_phase10_tables(db_path)

    # 3. Seed Default RBAC Accounts
    print("\n[*] Seeding default RBAC accounts (admin, operator, viewer)...")
    SecurityService.seed_default_users(db_path)
    print("    - Admin:    admin    / GridWise@Admin2026")
    print("    - Operator: operator / Operator@2026")
    print("    - Viewer:   viewer   / Viewer@2026")

    # 4. Create Initial Baseline Hot Backup
    print("\n[*] Creating baseline hot backup snapshot...")
    backup_result = BackupService.backup_database(db_path=db_path, tag="initial_production")
    if backup_result.get("status") == "success":
        print(f"    - Baseline snapshot created: {backup_result.get('filename')} ({backup_result.get('size_kb')} KB)")
    else:
        print(f"    - Backup warning: {backup_result.get('error')}")

    # 5. Health Check
    health = check_db_health()
    print(f"\n[*] Health Check: {health.get('status')} (Tables: {health.get('tables')}, FK violations: {health.get('foreign_key_violations')})")
    
    print("=" * 70)
    print("[SUCCESS] Production environment initialization complete.")
    print("=" * 70)

if __name__ == "__main__":
    init_production()

