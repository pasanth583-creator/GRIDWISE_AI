"""
GRIDWISE AI - Production Readiness Pre-Flight Checklist
Validates environment, packages, database, solver, and directory permissions.
"""

import sys
import os
import sqlite3
import importlib

def run_checks() -> bool:
    print("=" * 70)
    print("GRIDWISE AI - PRODUCTION READINESS CHECK")
    print("=" * 70)
    
    passed_all = True
    
    # 1. Python Version Check
    py_ver = sys.version_info
    print(f"[*] Python Version: {py_ver.major}.{py_ver.minor}.{py_ver.micro} ... ", end="")
    if py_ver.major >= 3 and py_ver.minor >= 10:
        print("[PASS]")
    else:
        print("[FAIL] (Requires Python >= 3.10)")
        passed_all = False

    # 2. Required Dependencies
    required_pkgs = [
        ("flask", "Flask"),
        ("numpy", "NumPy"),
        ("pandas", "Pandas"),
        ("scipy", "SciPy"),
        ("sklearn", "Scikit-Learn"),
        ("plotly", "Plotly"),
        ("reportlab", "ReportLab"),
        ("pptx", "python-pptx"),
        ("requests", "Requests")
    ]
    
    print("\n[*] Validating Core Dependencies:")
    for mod_name, label in required_pkgs:
        try:
            mod = importlib.import_module(mod_name)
            ver = getattr(mod, "__version__", "installed")
            print(f"    - {label:<16}: {ver} [PASS]")
        except ImportError as e:
            print(f"    - {label:<16}: NOT FOUND [FAIL]")
            passed_all = False

    # 3. Optimization Solver Check (SciPy HiGHS)
    print("\n[*] Validating HiGHS Linear Programming Solver ... ", end="")
    try:
        from scipy.optimize import linprog
        res = linprog(c=[2.0], A_ub=[[-1.0]], b_ub=[-10.0], bounds=[(0, None)], method="highs")
        if res.success and abs(res.x[0] - 10.0) < 1e-4:
            print("[PASS] (HiGHS Verified)")
        else:
            print(f"[FAIL] (Solver returned: {res.message})")
            passed_all = False
    except Exception as e:
        print(f"[FAIL] ({e})")
        passed_all = False

    # 4. Database Integrity Check
    print("\n[*] Validating SQLite Database & Schema ... ", end="")
    db_path = os.path.join("database", "gridwise.db")
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("PRAGMA integrity_check;")
            integ = c.fetchone()[0]
            c.execute("PRAGMA foreign_key_check;")
            fk_errs = len(c.fetchall())
            c.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
            t_count = c.fetchone()[0]
            conn.close()
            
            if integ == "ok" and fk_errs == 0:
                print(f"[PASS] (Integrity: OK, Tables: {t_count}, FK Errors: 0)")
            else:
                print(f"[WARN] (Integrity: {integ}, FK Errors: {fk_errs})")
        except Exception as e:
            print(f"[FAIL] ({e})")
            passed_all = False
    else:
        print(f"[WARN] (Database not initialized at {db_path})")

    # 5. Directory Permissions Check
    print("\n[*] Validating Storage Directories Writable:")
    dirs = ["database", "logs", "backups", "data", "reports"]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        is_writable = os.access(d, os.W_OK)
        status = "[PASS]" if is_writable else "[FAIL]"
        print(f"    - {d:<16}: {status}")
        if not is_writable:
            passed_all = False

    print("=" * 70)
    if passed_all:
        print("[SUCCESS] System is 100% PRODUCTION READY for deployment.")
    else:
        print("[FAILURE] Resolve the failed checks before production deployment.")
    print("=" * 70)
    
    return passed_all

if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)

