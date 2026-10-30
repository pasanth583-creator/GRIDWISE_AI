"""
GRIDWISE AI - Asynchronous Background Job Manager
Phase 10 Production Performance & Non-Blocking Optimization Execution

Features:
- Thread-pool worker execution (concurrent.futures)
- State management: QUEUED -> RUNNING -> COMPLETED / FAILED / CANCELLED
- Atomic state updates and SQLite persistence (background_jobs table)
- Real status and error details without fabricated progress percentages.
"""

from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timezone
import uuid
import json
import logging
import threading

from database.database import execute_db, query_db
from services.optimization_service import OptimizationService
from services.adaptive_optimization_service import AdaptiveOptimizationService

logger = logging.getLogger(__name__)


class BackgroundJobManager:
    """Thread-safe background job execution manager."""

    _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="GridWiseJob")
    _active_futures: Dict[str, Future] = {}
    _job_lock = threading.Lock()

    @classmethod
    def submit_optimization_job(
        cls,
        job_type: str = "ADAPTIVE_STOCHASTIC",
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Submits an optimization job to the asynchronous thread pool."""
        job_uuid = f"JOB-{uuid.uuid4().hex[:8].upper()}"
        job_params = params or {}
        now_iso = datetime.now(timezone.utc).isoformat()

        # Persist QUEUED state to SQLite
        try:
            execute_db(
                """
                INSERT INTO background_jobs (
                    job_uuid, job_type, status, params_json, created_at
                ) VALUES (?, ?, 'QUEUED', ?, ?)
                """,
                (job_uuid, job_type, json.dumps(job_params), now_iso),
            )
        except Exception as e:
            logger.error(f"Failed to record queued job in DB: {e}")

        # Submit task to ThreadPool
        with cls._job_lock:
            future = cls._executor.submit(cls._run_job_worker, job_uuid, job_type, job_params)
            cls._active_futures[job_uuid] = future

        return {
            "job_uuid": job_uuid,
            "job_id": job_uuid,
            "job_type": job_type,
            "status": "QUEUED",
            "created_at": now_iso,
            "params": job_params,
        }

    @classmethod
    def _run_job_worker(cls, job_uuid: str, job_type: str, params: Dict[str, Any]) -> None:
        """Internal worker function running on a background thread."""
        logger.info(f"Starting execution of background job {job_uuid} ({job_type})")
        start_iso = datetime.now(timezone.utc).isoformat()

        # Update status to RUNNING
        try:
            execute_db(
                "UPDATE background_jobs SET status = 'RUNNING', started_at = ? WHERE job_uuid = ?",
                (start_iso, job_uuid),
            )
        except Exception:
            pass

        try:
            # Check cancellation flag before running heavy solver
            with cls._job_lock:
                fut = cls._active_futures.get(job_uuid)
                if fut and fut.cancelled():
                    cls._mark_cancelled(job_uuid)
                    return

            # Execute actual optimization
            num_scenarios = int(params.get("num_scenarios", 50))
            risk_lambda = float(params.get("risk_aversion", 0.0))
            battery_cap = float(params.get("battery_capacity_kwh", 1000.0))

            if job_type == "ADAPTIVE_STOCHASTIC":
                result = AdaptiveOptimizationService.run_adaptive_optimization(
                    num_scenarios=num_scenarios,
                    risk_aversion_lambda=risk_lambda,
                    battery_capacity_kwh=battery_cap,
                )
            else:
                result = OptimizationService.run_optimization(
                    num_scenarios=num_scenarios,
                    risk_aversion_lambda=risk_lambda,
                    battery_capacity_kwh=battery_cap,
                )

            comp_iso = datetime.now(timezone.utc).isoformat()
            try:
                execute_db(
                    """
                    UPDATE background_jobs
                    SET status = 'COMPLETED', result_json = ?, completed_at = ?
                    WHERE job_uuid = ?
                    """,
                    (json.dumps(result), comp_iso, job_uuid),
                )
            except Exception as e:
                logger.error(f"Error persisting completed job: {e}")

            logger.info(f"Background job {job_uuid} completed successfully.")

        except Exception as e:
            logger.exception(f"Background job {job_uuid} failed with error: {e}")
            fail_iso = datetime.now(timezone.utc).isoformat()
            try:
                execute_db(
                    """
                    UPDATE background_jobs
                    SET status = 'FAILED', error_message = ?, completed_at = ?
                    WHERE job_uuid = ?
                    """,
                    (str(e), fail_iso, job_uuid),
                )
            except Exception:
                pass
        finally:
            with cls._job_lock:
                cls._active_futures.pop(job_uuid, None)

    @classmethod
    def cancel_job(cls, job_uuid: str) -> Dict[str, Any]:
        """Cancels a job if it is still QUEUED; marks CANCELLED."""
        with cls._job_lock:
            fut = cls._active_futures.get(job_uuid)
            if fut and not fut.running() and not fut.done():
                fut.cancel()
                cls._mark_cancelled(job_uuid)
                return {"job_id": job_uuid, "status": "CANCELLED", "message": "Job successfully cancelled."}

        # Check DB status
        row = cls.get_job_status(job_uuid)
        if row and row["status"] == "QUEUED":
            cls._mark_cancelled(job_uuid)
            return {"job_id": job_uuid, "status": "CANCELLED", "message": "Job cancelled."}

        return {
            "job_id": job_uuid,
            "status": row.get("status") if row else "NOT_FOUND",
            "message": "Cannot cancel job that is already running, completed, or failed.",
        }

    @classmethod
    def _mark_cancelled(cls, job_uuid: str) -> None:
        """Helper to mark CANCELLED in DB."""
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            execute_db(
                "UPDATE background_jobs SET status = 'CANCELLED', completed_at = ? WHERE job_uuid = ?",
                (now_iso, job_uuid),
            )
        except Exception:
            pass

    @classmethod
    def get_job_status(cls, job_uuid: str) -> Optional[Dict[str, Any]]:
        """Queries single job status from SQLite."""
        try:
            row = query_db(
                "SELECT * FROM background_jobs WHERE job_uuid = ?",
                (job_uuid,),
                one=True,
            )
            if not row:
                return None
            d = dict(row)
            try:
                d["params"] = json.loads(d["params_json"])
            except Exception:
                d["params"] = {}
            if d.get("result_json"):
                try:
                    d["result"] = json.loads(d["result_json"])
                except Exception:
                    d["result"] = None
            return d
        except Exception as e:
            logger.error(f"Error querying job {job_uuid}: {e}")
            return None

    @classmethod
    def list_jobs(cls, limit: int = 20) -> List[Dict[str, Any]]:
        """Queries recent jobs sorted newest first."""
        try:
            rows = query_db(
                "SELECT job_uuid, job_type, status, error_message, created_at, started_at, completed_at FROM background_jobs ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error listing jobs: {e}")
            return []

    @classmethod
    def list_recent_jobs(cls, limit: int = 20) -> List[Dict[str, Any]]:
        """Alias for list_jobs."""
        return cls.list_jobs(limit=limit)

    @classmethod
    def enqueue_optimization_job(
        cls,
        scenarios_count: int = 100,
        risk_lambda: float = 0.0,
        user_id: Optional[str] = None
    ) -> str:
        """Enqueues stochastic optimization and returns job_uuid."""
        res = cls.submit_optimization_job(
            job_type="STOCHASTIC_OPTIMIZATION",
            params={"scenarios_count": scenarios_count, "risk_lambda": risk_lambda, "user_id": user_id}
        )
        return res["job_uuid"]

# Convenience module-level aliases
job_manager = BackgroundJobManager
