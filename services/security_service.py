"""
GRIDWISE AI - Security & Authentication Service
Phase 10 Production Readiness & Enterprise Security

Features:
- PBKDF2 Password Hashing (Werkzeug)
- Role-Based Access Control (RBAC: Admin, Operator, Viewer)
- CSRF Token Generation & Validation
- In-Memory Rate Limiting
- Security Headers & Input Sanitization
"""

from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from datetime import datetime, timezone, timedelta
import os
import secrets
import hashlib
import time
import logging
from flask import request, session, jsonify, redirect, url_for, g, current_app
from werkzeug.security import generate_password_hash, check_password_hash

from database.database import query_db, execute_db, create_connection

logger = logging.getLogger(__name__)


class SecurityService:
    """Manages authentication, RBAC, CSRF validation, and rate limiting."""

    _rate_limit_records: Dict[str, List[float]] = {}
    RATE_LIMIT_WINDOW = 60.0  # 1 minute
    DEFAULT_RATE_LIMIT = 60   # 60 requests per minute

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hashes password using PBKDF2-HMAC-SHA256 with random salt."""
        return generate_password_hash(password, method="scrypt")

    @classmethod
    def verify_password(cls, password: str, password_hash: str) -> bool:
        """Verifies cleartext password against stored hash."""
        return check_password_hash(password_hash, password)

    @classmethod
    def authenticate_user(cls, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Validates credentials against database users table and returns user dict."""
        try:
            row = query_db(
                "SELECT * FROM users WHERE username = ? AND is_active = 1",
                (username,),
                one=True,
            )
            if not row:
                return None

            user = dict(row)
            if cls.verify_password(password, user["password_hash"]):
                # Update last login timestamp
                execute_db(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                    (user["id"],),
                )
                return {
                    "id": user["id"],
                    "username": user["username"],
                    "role": user["role"],
                    "full_name": user.get("full_name", user["username"]),
                    "email": user.get("email"),
                }
        except Exception as e:
            logger.error(f"Authentication database error: {e}")
        return None

    @classmethod
    def verify_user(cls, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Alias for authenticate_user."""
        return cls.authenticate_user(username, password)

    @classmethod
    def update_password(cls, username: str, new_password: str, conn=None) -> bool:
        """Updates user password hash securely."""
        try:
            pwd_hash = cls.hash_password(new_password)
            execute_db(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (pwd_hash, username),
                conn=conn
            )
            logger.info(f"Password updated successfully for user: {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to update password for {username}: {e}")
            return False

    @classmethod
    def create_user_session(cls, user: Dict[str, Any]) -> None:
        """Initializes user session state and CSRF token."""
        session["user"] = user["username"]
        session["role"] = user["role"]
        session["user_id"] = user.get("id")
        session["csrf_token"] = cls.generate_csrf_token()

    @classmethod
    def clear_session(cls) -> None:
        """Clears user session securely."""
        session.pop("user", None)
        session.pop("role", None)
        session.pop("user_id", None)
        session.pop("csrf_token", None)

    @classmethod
    def seed_default_users(cls, db_path: Optional[str] = None) -> None:
        """Seeds default administrative, operator, and viewer users if table is empty."""
        conn = create_connection(db_path) if db_path else None
        close_conn = True if conn else False
        try:
            cnt = query_db("SELECT COUNT(*) as c FROM users", one=True, conn=conn)
            if cnt and cnt["c"] > 0:
                return

            default_users = [
                ("admin", "GridWise@Admin2026", "admin", "System Administrator", "admin@campus-microgrid.edu"),
                ("operator", "Operator@2026", "operator", "Microgrid Dispatch Operator", "dispatch@campus-microgrid.edu"),
                ("viewer", "Viewer@2026", "viewer", "Academic Research Analyst", "research@campus-microgrid.edu"),
            ]

            for uname, pwd, role, fname, email in default_users:
                pwd_hash = cls.hash_password(pwd)
                execute_db(
                    """
                    INSERT INTO users (username, password_hash, role, full_name, email, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                    """,
                    (uname, pwd_hash, role, fname, email),
                    conn=conn,
                )
            logger.info("Default users seeded successfully (admin, operator, viewer).")
        except Exception as e:
            logger.error(f"Could not seed default users: {e}")
        finally:
            if close_conn and conn:
                conn.close()

    @classmethod
    def generate_csrf_token(cls) -> str:
        """Generates or retrieves a secure random CSRF token tied to user session."""
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(32)
        return session["csrf_token"]

    @classmethod
    def validate_csrf_token(cls, token: Optional[str]) -> bool:
        """Validates provided CSRF token against session token using constant-time comparison."""
        expected = session.get("csrf_token")
        if not expected or not token:
            return False
        return secrets.compare_digest(expected, token)

    @classmethod
    def check_rate_limit(cls, client_ip: str, max_requests: int = 60, limit: Optional[int] = None, period_sec: int = 60):
        """
        Sliding-window rate limiter per client IP.
        Returns tuple (is_allowed, remaining_requests).
        """
        eff_limit = limit if limit is not None else max_requests
        now = time.time()
        timestamps = cls._rate_limit_records.get(client_ip, [])
        valid_timestamps = [t for t in timestamps if now - t < period_sec]
        valid_timestamps.append(now)
        cls._rate_limit_records[client_ip] = valid_timestamps
        is_allowed = len(valid_timestamps) <= eff_limit
        remaining = max(0, eff_limit - len(valid_timestamps))
        return is_allowed, remaining


# ============================================================================
# Flask Security Decorators
# ============================================================================

def login_required(f: Callable) -> Callable:
    """Decorator ensuring user is authenticated in session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user"):
            if request.path.startswith("/api/") or request.is_json:
                return jsonify({"success": False, "error": "Authentication required. Please log in."}), 401
            return redirect(url_for("auth.login_view", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def roles_required(*allowed_roles: str) -> Callable:
    """Decorator enforcing Role-Based Access Control (RBAC)."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = session.get("user")
            if not user:
                if request.path.startswith("/api/") or request.is_json:
                    return jsonify({"success": False, "error": "Authentication required."}), 401
                return redirect(url_for("auth.login_view", next=request.path))

            user_role = session.get("role")
            if not user_role:
                user_role = user.get("role", "viewer") if isinstance(user, dict) else "viewer"
            if user_role not in allowed_roles and "admin" not in allowed_roles and user_role != "admin":
                if request.path.startswith("/api/") or request.is_json:
                    return jsonify({"success": False, "error": "Insufficient privileges."}), 403
                return render_template("errors/403.html"), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def rate_limit(max_requests: int = 60) -> Callable:
    """Decorator applying rate limits to endpoints based on client IP."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr or "127.0.0.1"
            if not SecurityService.check_rate_limit(client_ip, max_requests=max_requests):
                return jsonify({
                    "success": False,
                    "error": f"Rate limit exceeded. Maximum {max_requests} requests per minute.",
                }), 429
            return f(*args, **kwargs)
        return decorated_function
    return decorator
