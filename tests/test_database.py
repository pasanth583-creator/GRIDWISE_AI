"""
GRIDWISE AI - Database Management Tests
Validates schema creation, health checks, CRUD queries, and error handling.
"""

import os
import tempfile
import pytest
from database.database import (
    create_connection,
    init_db,
    query_db,
    execute_db,
    check_db_health,
)


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database file for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_database_initialization(temp_db):
    """Verify that all required microgrid tables are created."""
    health = check_db_health(temp_db)
    assert health["status"] == "HEALTHY"
    assert health["connected"] is True
    assert health["table_count"] >= 8

    required_tables = [
        "microgrid_config",
        "energy_prices",
        "solar_forecasts",
        "campus_load_forecasts",
        "optimization_runs",
        "optimization_schedule",
        "stochastic_scenarios",
        "system_health_audit",
    ]
    for table in required_tables:
        assert table in health["tables"], f"Table {table} missing from schema"


def test_microgrid_seed_config(temp_db):
    """Verify default campus configuration seed is inserted."""
    conn = create_connection(temp_db)
    row = query_db(
        "SELECT * FROM microgrid_config WHERE config_name = ?;",
        ("Campus Main Microgrid",),
        one=True,
        conn=conn,
    )
    conn.close()

    assert row is not None
    assert row["pv_capacity_kw"] == 800.0
    assert row["bess_capacity_kwh"] == 1000.0
    assert row["bess_max_power_kw"] == 400.0


def test_execute_and_query_db(temp_db):
    """Verify inserting and querying custom audit records."""
    conn = create_connection(temp_db)
    res = execute_db(
        "INSERT INTO system_health_audit (component, status, metric_value, message) VALUES (?, ?, ?, ?);",
        ("UNIT_TEST", "OK", "99.9", "Test run passed"),
        conn=conn,
    )
    assert res["lastrowid"] > 0

    records = query_db(
        "SELECT * FROM system_health_audit WHERE component = ?;",
        ("UNIT_TEST",),
        conn=conn,
    )
    conn.close()

    assert len(records) == 1
    assert records[0]["status"] == "OK"
    assert records[0]["metric_value"] == "99.9"

