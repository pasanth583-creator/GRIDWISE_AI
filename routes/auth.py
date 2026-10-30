"""
GRIDWISE AI - Authentication and Authorization Routes
Provides user login, logout, session management, and RBAC enforcement.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from services.security_service import SecurityService, login_required

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login_view():
    """Renders login interface or processes authentication."""
    if request.method == "POST":
        ip = request.remote_addr or "127.0.0.1"
        is_allowed, remaining = SecurityService.check_rate_limit(f"login_{ip}", limit=10, period_sec=60)
        if not is_allowed:
            flash("Too many failed login attempts. Please wait 1 minute before trying again.", "danger")
            return render_template("login.html", error="Rate limit exceeded. Try again in 60 seconds."), 429

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        next_url = request.args.get("next") or request.form.get("next") or url_for("dashboard.dashboard_view")

        user = SecurityService.verify_user(username, password)
        if user:
            SecurityService.create_user_session(user)
            flash(f"Welcome back, {user['username']}! Logged in with {user['role'].upper()} privileges.", "success")
            return redirect(next_url)
        else:
            flash("Invalid username or password. Please verify your credentials.", "danger")
            return render_template("login.html", error="Invalid username or password", username=username), 401

    if session.get("user"):
        return redirect(url_for("dashboard.dashboard_view"))
        
    return render_template("login.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout_view():
    """Logs out the active user and invalidates session."""
    user = session.get("user")
    SecurityService.clear_session()
    if user:
        flash("You have been logged out securely.", "info")
    return redirect(url_for("auth.login_view"))


@auth_bp.route("/api/auth/csrf", methods=["GET"])
def get_csrf_token():
    """Generates and returns a CSRF token for API clients."""
    token = SecurityService.generate_csrf_token()
    return jsonify({
        "status": "success",
        "csrf_token": token
    })


@auth_bp.route("/api/auth/me", methods=["GET"])
def current_user_info():
    """Returns profile and role of currently authenticated user."""
    user = session.get("user")
    role = session.get("role")
    if user:
        return jsonify({
            "authenticated": True,
            "username": user,
            "role": role,
            "permissions": {
                "can_run_optimization": role in ["admin", "operator"],
                "can_trigger_backup": role in ["admin", "operator"],
                "can_restore_backup": role == "admin",
                "can_manage_users": role == "admin"
            }
        })
    return jsonify({
        "authenticated": False,
        "username": None,
        "role": "anonymous"
    })

