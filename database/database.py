"""
GRIDWISE AI - Database Management Module
SQLite connection handling, schema migration, and query execution.
"""

import os
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from flask import g, current_app

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_db_path(app=None):
    """Retrieve the resolved database path from Flask app config or default."""
    if app:
        return app.config.get("DATABASE_PATH", "database/gridwise.db")
    if current_app:
        return current_app.config.get("DATABASE_PATH", "database/gridwise.db")
    from config import get_config
    return get_config().DATABASE_PATH


def create_connection(db_path=None):
    """Create a new SQLite connection with optimal PRAGMA settings."""
    if not db_path:
        db_path = get_db_path()

    # Ensure parent directory exists for file-based DB
    if db_path != ":memory:":
        parent_dir = Path(db_path).parent
        parent_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        db_path,
        timeout=20.0,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def get_db():
    """
    Get or create database connection for the current Flask application context.
    Falls back to a new connection if invoked outside of request context.
    """
    try:
        if "db" not in g:
            db_path = get_db_path(current_app)
            g.db = create_connection(db_path)
        return g.db
    except RuntimeError:
        # Working outside of Flask application context
        return create_connection()


def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop("db", None) if hasattr(g, "db") else None
    if db is not None:
        try:
            db.close()
        except Exception as ex:
            logger.error(f"Error closing DB connection: {ex}")


@contextmanager
def get_db_context(db_path=None):
    """Context manager for non-request DB transactions or CLI operations."""
    conn = create_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception as ex:
        conn.rollback()
        logger.error(f"Database transaction error: {ex}")
        raise
    finally:
        conn.close()


def init_db(db_path=None, schema_file=None):
    """Initialize database tables and initial seeds from schema.sql."""
    if not schema_file:
        schema_file = SCHEMA_PATH

    resolved_path = db_path if db_path else get_db_path()
    logger.info(f"Initializing database at: {resolved_path}")

    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_db_context(resolved_path) as conn:
        conn.executescript(schema_sql)

    logger.info("Database schema applied successfully.")
    return True


def query_db(query, args=(), one=False, conn=None):
    """Execute a read query and return list of dicts (or single dict)."""
    close_after = False
    if conn is None:
        try:
            conn = get_db()
        except Exception:
            conn = create_connection()
            close_after = True

    try:
        cursor = conn.cursor()
        cursor.execute(query, args)
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        return (result[0] if result else None) if one else result
    finally:
        if close_after and conn:
            conn.close()


def execute_db(query, args=(), commit=True, conn=None):
    """Execute an INSERT/UPDATE/DELETE query and return lastrowid / rowcount."""
    close_after = False
    if conn is None:
        try:
            conn = get_db()
        except Exception:
            conn = create_connection()
            close_after = True

    try:
        cursor = conn.cursor()
        cursor.execute(query, args)
        if commit:
            conn.commit()
        return {
            "lastrowid": cursor.lastrowid,
            "rowcount": cursor.rowcount,
        }
    finally:
        if close_after and conn:
            conn.close()


def migrate_phase8_tables(db_path=None):
    """
    Safely executes Phase 8 schema additions to create weather, adaptive forecast,
    and alert tables if they do not exist, without altering or dropping existing tables.
    """
    resolved_path = db_path if db_path else get_db_path()
    logger.info(f"Applying Phase 8 SQLite migrations to: {resolved_path}")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_db_context(resolved_path) as conn:
        conn.executescript(schema_sql)

    logger.info("Phase 8 migrations applied successfully.")
    return True


def migrate_phase9_tables(db_path=None):
    """
    Safely executes Phase 9 schema additions to create decision explanations,
    recommendations, multi-objective runs, Pareto solutions, What-If experiments,
    and battery lifecycle metrics without altering or dropping existing tables.
    """
    resolved_path = db_path if db_path else get_db_path()
    logger.info(f"Applying Phase 9 SQLite migrations to: {resolved_path}")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_db_context(resolved_path) as conn:
        conn.executescript(schema_sql)

    logger.info("Phase 9 migrations applied successfully.")
    return True


def migrate_phase10_tables(db_path=None):
    """
    Safely executes Phase 10 schema additions for users, RBAC, and background jobs.
    Preserves all existing database records.
    """
    resolved_path = db_path if db_path else get_db_path()
    logger.info(f"Applying Phase 10 SQLite migrations to: {resolved_path}")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_db_context(resolved_path) as conn:
        conn.executescript(schema_sql)

    # Seed default users
    from services.security_service import SecurityService
    SecurityService.seed_default_users()

    logger.info("Phase 10 migrations applied and default users verified.")
    return True




def check_db_health(db_path=None):
    """Health check utility to verify database connectivity and table status."""
    try:
        resolved_path = db_path if db_path else get_db_path()
        conn = create_connection(resolved_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall() if not row["name"].startswith("sqlite_")]

        # Count records in microgrid_config if available
        config_count = 0
        if "microgrid_config" in tables:
            cursor.execute("SELECT COUNT(*) AS cnt FROM microgrid_config;")
            row = cursor.fetchone()
            config_count = row["cnt"] if row else 0

        # Run integrity check
        cursor.execute("PRAGMA integrity_check;")
        integrity_row = cursor.fetchone()
        integrity_status = integrity_row[0] if integrity_row else "ok"

        # Run foreign key check
        cursor.execute("PRAGMA foreign_key_check;")
        fk_violations = len(cursor.fetchall())

        conn.close()

        file_size = 0
        if resolved_path != ":memory:" and os.path.exists(resolved_path):
            file_size = os.path.getsize(resolved_path)

        return {
            "status": "HEALTHY" if integrity_status == "ok" and fk_violations == 0 else "WARNING",
            "database_path": str(resolved_path),
            "tables": tables,
            "table_count": len(tables),
            "configured_microgrids": config_count,
            "integrity_check": integrity_status,
            "foreign_key_violations": fk_violations,
            "size_bytes": file_size,
            "connected": True,
        }
    except Exception as e:
        logger.exception("Database health check failed")
        return {
            "status": "UNHEALTHY",
            "error": str(e),
            "connected": False,
        }


def init_app(app):
    """Register database teardown and custom Flask CLI commands."""
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        """Initialize the database schema."""
        init_db(app.config.get("DATABASE_PATH"))
        print(f"Initialized database successfully at: {app.config.get('DATABASE_PATH')}")
