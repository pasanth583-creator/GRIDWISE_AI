"""
GRIDWISE AI - System Health Service
Comprehensive diagnostics for Database, LP Solver, Forecasting Engine, Weather Service, and Filesystem.
"""

import os
import sys
import time
import sqlite3
import platform
from typing import Dict, Any
from config import Config, BASE_DIR

class SystemHealthService:
    """Executes live diagnostic health checks across all subsystem dependencies."""
    
    @staticmethod
    def check_database() -> Dict[str, Any]:
        """Validates SQLite connection, table count, foreign keys, and integrity."""
        db_path = Config.DATABASE_PATH
        if not os.path.exists(db_path):
            return {
                "status": "unhealthy",
                "message": f"Database file missing at {db_path}",
                "tables_count": 0,
                "integrity": "missing"
            }
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Integrity check
            cursor.execute("PRAGMA integrity_check;")
            integrity_row = cursor.fetchone()
            integrity = integrity_row[0] if integrity_row else "unknown"
            
            # Foreign key check
            cursor.execute("PRAGMA foreign_key_check;")
            fk_violations = len(cursor.fetchall())
            
            # Tables count
            cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
            table_count = cursor.fetchone()[0]
            
            size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 2)
            conn.close()
            
            is_ok = (integrity == "ok" and fk_violations == 0)
            return {
                "status": "healthy" if is_ok else "degraded",
                "integrity": integrity,
                "foreign_key_violations": fk_violations,
                "table_count": table_count,
                "size_mb": size_mb,
                "path": db_path
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    @staticmethod
    def check_solver() -> Dict[str, Any]:
        """Validates SciPy HiGHS LP solver capability with a test problem."""
        t0 = time.time()
        try:
            from scipy.optimize import linprog
            # Min x s.t. x >= 5, x >= 0  => x* = 5
            res = linprog(c=[1.0], A_ub=[[-1.0]], b_ub=[-5.0], bounds=[(0, None)], method='highs')
            elapsed_ms = round((time.time() - t0) * 1000, 2)
            if res.success and abs(res.x[0] - 5.0) < 1e-4:
                return {
                    "status": "healthy",
                    "solver": "highs",
                    "latency_ms": elapsed_ms,
                    "verified": True
                }
            else:
                return {
                    "status": "unhealthy",
                    "solver": "highs",
                    "error": res.message
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "solver": "highs",
                "error": str(e)
            }

    @staticmethod
    def check_forecasting() -> Dict[str, Any]:
        """Validates forecasting module availability and data directories."""
        try:
            from forecasting.demand_forecaster import CampusDemandForecaster
            from forecasting.solar_forecaster import CampusSolarForecaster
            from forecasting.price_forecaster import ElectricityPriceForecaster
            
            data_forecast_dir = os.path.join(BASE_DIR, "data", "forecasts")
            has_forecast_dir = os.path.exists(data_forecast_dir)
            
            return {
                "status": "healthy",
                "modules_loaded": True,
                "forecast_data_dir_exists": has_forecast_dir
            }
        except Exception as e:
            return {
                "status": "degraded",
                "modules_loaded": False,
                "error": str(e)
            }

    @staticmethod
    def check_weather_service() -> Dict[str, Any]:
        """Validates weather service configuration and caching."""
        try:
            from services.weather_service import weather_service
            cache_file = weather_service.cache_file
            cache_exists = os.path.exists(cache_file)
            return {
                "status": "healthy",
                "provider": "Open-Meteo",
                "latitude": weather_service.latitude,
                "longitude": weather_service.longitude,
                "cache_file_exists": cache_exists
            }
        except Exception as e:
            return {
                "status": "degraded",
                "error": str(e)
            }

    @staticmethod
    def check_filesystem() -> Dict[str, Any]:
        """Verifies read/write permissions for essential directories."""
        required_dirs = ["data", "database", "logs", "backups", "reports"]
        dir_status = {}
        all_writable = True
        
        for d in required_dirs:
            full_path = os.path.join(BASE_DIR, d)
            os.makedirs(full_path, exist_ok=True)
            writable = os.access(full_path, os.W_OK)
            dir_status[d] = {"exists": os.path.exists(full_path), "writable": writable}
            if not writable:
                all_writable = False
                
        return {
            "status": "healthy" if all_writable else "degraded",
            "directories": dir_status
        }

    @classmethod
    def get_full_diagnostics(cls) -> Dict[str, Any]:
        """Returns complete system diagnostics with aggregate health score."""
        db = cls.check_database()
        solver = cls.check_solver()
        forecasting = cls.check_forecasting()
        weather = cls.check_weather_service()
        filesystem = cls.check_filesystem()
        
        statuses = [db.get("status"), solver.get("status"), filesystem.get("status")]
        if any(s == "unhealthy" for s in statuses):
            overall_status = "unhealthy"
        elif any(s == "degraded" for s in [db.get("status"), forecasting.get("status"), weather.get("status"), filesystem.get("status")]):
            overall_status = "degraded"
        else:
            overall_status = "healthy"
            
        return {
            "status": overall_status,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "environment": {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "architecture": platform.machine()
            },
            "components": {
                "database": db,
                "solver": solver,
                "forecasting": forecasting,
                "weather_service": weather,
                "filesystem": filesystem
            }
        }
