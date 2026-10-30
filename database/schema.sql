-- GRIDWISE AI - Database Schema
-- Stochastic Optimization of Day-Ahead Energy Procurement for a Campus Solar + Battery Microgrid

PRAGMA foreign_keys = ON;

-- 1. Microgrid System Configuration
CREATE TABLE IF NOT EXISTS microgrid_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_name TEXT NOT NULL UNIQUE,
    pv_capacity_kw REAL NOT NULL DEFAULT 750.0,
    bess_capacity_kwh REAL NOT NULL DEFAULT 1200.0,
    bess_max_power_kw REAL NOT NULL DEFAULT 400.0,
    bess_charge_efficiency REAL NOT NULL DEFAULT 0.94,
    bess_discharge_efficiency REAL NOT NULL DEFAULT 0.94,
    min_soc REAL NOT NULL DEFAULT 0.15,
    max_soc REAL NOT NULL DEFAULT 0.95,
    initial_soc REAL NOT NULL DEFAULT 0.50,
    grid_import_limit_kw REAL NOT NULL DEFAULT 1000.0,
    grid_export_limit_kw REAL NOT NULL DEFAULT 500.0,
    demand_charge_rate REAL NOT NULL DEFAULT 12.50,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Day-Ahead Electricity Market Prices (24-Hour Horizon)
CREATE TABLE IF NOT EXISTS energy_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    forecast_date TEXT NOT NULL,
    hour INTEGER NOT NULL CHECK (hour >= 0 AND hour <= 23),
    buy_price_per_kwh REAL NOT NULL,
    sell_price_per_kwh REAL NOT NULL,
    tariff_period TEXT NOT NULL, -- 'Off-Peak', 'Shoulder', 'On-Peak'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(forecast_date, hour)
);

-- 3. Day-Ahead Solar PV Forecast (24-Hour Horizon)
CREATE TABLE IF NOT EXISTS solar_forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    forecast_date TEXT NOT NULL,
    hour INTEGER NOT NULL CHECK (hour >= 0 AND hour <= 23),
    ghi_w_m2 REAL DEFAULT 0.0,
    expected_generation_kw REAL NOT NULL DEFAULT 0.0,
    lower_bound_kw REAL DEFAULT 0.0,
    upper_bound_kw REAL DEFAULT 0.0,
    confidence_level REAL DEFAULT 0.90,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(forecast_date, hour)
);

-- 4. Day-Ahead Campus Electrical Demand Forecast (24-Hour Horizon)
CREATE TABLE IF NOT EXISTS campus_load_forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    forecast_date TEXT NOT NULL,
    hour INTEGER NOT NULL CHECK (hour >= 0 AND hour <= 23),
    expected_load_kw REAL NOT NULL,
    lower_bound_kw REAL DEFAULT 0.0,
    upper_bound_kw REAL DEFAULT 0.0,
    campus_session TEXT DEFAULT 'Academic Semester',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(forecast_date, hour)
);

-- 5. Optimization Runs Metadata
CREATE TABLE IF NOT EXISTS optimization_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_uuid TEXT NOT NULL UNIQUE,
    run_name TEXT NOT NULL,
    run_date TEXT NOT NULL,
    formulation_type TEXT NOT NULL DEFAULT 'Two-Stage Stochastic',
    status TEXT NOT NULL DEFAULT 'INITIALIZED', -- 'INITIALIZED', 'RUNNING', 'COMPLETED', 'FAILED'
    num_scenarios INTEGER DEFAULT 50,
    solver_name TEXT DEFAULT 'SciPy HiGHS / Interior-Point',
    total_procurement_cost REAL DEFAULT 0.0,
    baseline_cost REAL DEFAULT 0.0,
    cost_savings_pct REAL DEFAULT 0.0,
    total_solar_used_kwh REAL DEFAULT 0.0,
    total_grid_imported_kwh REAL DEFAULT 0.0,
    total_grid_exported_kwh REAL DEFAULT 0.0,
    total_battery_cycled_kwh REAL DEFAULT 0.0,
    solver_runtime_sec REAL DEFAULT 0.0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Optimal 24-Hour Dispatch Schedule
CREATE TABLE IF NOT EXISTS optimization_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    hour INTEGER NOT NULL CHECK (hour >= 0 AND hour <= 23),
    grid_import_kw REAL NOT NULL DEFAULT 0.0,
    grid_export_kw REAL NOT NULL DEFAULT 0.0,
    solar_used_kw REAL NOT NULL DEFAULT 0.0,
    solar_curtailed_kw REAL NOT NULL DEFAULT 0.0,
    bess_charge_kw REAL NOT NULL DEFAULT 0.0,
    bess_discharge_kw REAL NOT NULL DEFAULT 0.0,
    bess_soc_kwh REAL NOT NULL DEFAULT 600.0,
    bess_soc_pct REAL NOT NULL DEFAULT 50.0,
    campus_load_kw REAL NOT NULL DEFAULT 0.0,
    hourly_cost REAL NOT NULL DEFAULT 0.0,
    UNIQUE(run_id, hour)
);

-- 7. Stochastic Scenarios
CREATE TABLE IF NOT EXISTS stochastic_scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_group TEXT NOT NULL,
    scenario_index INTEGER NOT NULL,
    scenario_name TEXT NOT NULL,
    probability REAL NOT NULL,
    solar_multiplier REAL NOT NULL DEFAULT 1.0,
    load_multiplier REAL NOT NULL DEFAULT 1.0,
    price_multiplier REAL NOT NULL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(scenario_group, scenario_index)
);

-- 8. System Health and Audit Logs
CREATE TABLE IF NOT EXISTS system_health_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('OK', 'WARNING', 'ERROR')),
    metric_value TEXT,
    message TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_prices_date ON energy_prices(forecast_date);
CREATE INDEX IF NOT EXISTS idx_solar_date ON solar_forecasts(forecast_date);
CREATE INDEX IF NOT EXISTS idx_load_date ON campus_load_forecasts(forecast_date);
CREATE INDEX IF NOT EXISTS idx_runs_date ON optimization_runs(run_date);
CREATE INDEX IF NOT EXISTS idx_schedule_run ON optimization_schedule(run_id);

-- Default Campus Configuration Seed
INSERT OR IGNORE INTO microgrid_config (
    id, config_name, pv_capacity_kw, bess_capacity_kwh, bess_max_power_kw,
    bess_charge_efficiency, bess_discharge_efficiency,
    min_soc, max_soc, initial_soc,
    grid_import_limit_kw, grid_export_limit_kw, demand_charge_rate, is_active
) VALUES (
    1, 'Campus Main Microgrid', 800.0, 1000.0, 400.0,
    0.92, 0.92,
    0.15, 0.95, 0.50,
    1000.0, 500.0, 14.50, 1
);

-- Initial Audit Record
INSERT OR IGNORE INTO system_health_audit (
    id, component, status, metric_value, message
) VALUES (
    1, 'DATABASE', 'OK', 'SQLite Schema Ready', 'GridWise AI database schema created successfully'
);

-- ============================================================================
-- PHASE 8: LIVE WEATHER, ADAPTIVE FORECASTS & REAL-TIME INTELLIGENCE TABLES
-- ============================================================================

-- 9. Live & Hourly Weather Records (Open-Meteo Integration)
CREATE TABLE IF NOT EXISTS weather_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    location_name TEXT NOT NULL DEFAULT 'Tiruchirappalli, Tamil Nadu',
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    temperature_c REAL,
    relative_humidity_pct REAL,
    precipitation_mm REAL,
    precipitation_probability_pct REAL,
    cloud_cover_pct REAL,
    wind_speed_kmh REAL,
    solar_radiation_w_m2 REAL,
    direct_radiation_w_m2 REAL,
    diffuse_radiation_w_m2 REAL,
    data_source TEXT DEFAULT 'Open-Meteo Live API',
    is_cached INTEGER DEFAULT 0,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Adaptive Microgrid 24-Hour Forecasts
CREATE TABLE IF NOT EXISTS adaptive_forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    forecast_uuid TEXT NOT NULL,
    forecast_date TEXT NOT NULL,
    hour INTEGER NOT NULL CHECK (hour >= 0 AND hour <= 23),
    weather_condition TEXT,
    temperature_c REAL,
    cloud_cover_pct REAL,
    solar_radiation_w_m2 REAL,
    adaptive_solar_kw REAL NOT NULL,
    adaptive_demand_kw REAL NOT NULL,
    adaptive_da_price_inr REAL NOT NULL,
    adaptive_rt_price_inr REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(forecast_uuid, hour)
);

-- 11. Adaptive Scenario Generation Summaries
CREATE TABLE IF NOT EXISTS adaptive_scenario_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary_uuid TEXT NOT NULL UNIQUE,
    num_scenarios INTEGER NOT NULL,
    random_seed INTEGER NOT NULL,
    mean_daily_solar_kwh REAL,
    mean_daily_demand_kwh REAL,
    mean_da_price_inr REAL,
    mean_rt_price_inr REAL,
    weather_summary TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. Adaptive Optimization Runs & Comparisons
CREATE TABLE IF NOT EXISTS adaptive_optimization_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_uuid TEXT NOT NULL UNIQUE,
    run_name TEXT NOT NULL,
    run_date TEXT NOT NULL,
    data_source TEXT DEFAULT 'Open-Meteo + Adaptive ML',
    num_scenarios INTEGER NOT NULL,
    expected_cost_inr REAL NOT NULL,
    var_95_inr REAL NOT NULL,
    cvar_95_inr REAL NOT NULL,
    vss_inr REAL DEFAULT 0.0,
    vss_pct REAL DEFAULT 0.0,
    previous_run_uuid TEXT,
    cost_delta_inr REAL DEFAULT 0.0,
    cvar_delta_inr REAL DEFAULT 0.0,
    solver_status TEXT NOT NULL DEFAULT 'OPTIMAL',
    solve_time_sec REAL DEFAULT 0.0,
    day_ahead_schedule_json TEXT,
    battery_dispatch_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 13. Intelligent Energy & Microgrid System Alerts
CREATE TABLE IF NOT EXISTS energy_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_uuid TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL, -- 'Solar Reduction', 'Demand Surge', 'High Cost', 'Battery Readiness', 'CVaR Risk', 'Grid Procurement Change'
    severity TEXT NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL')),
    triggering_metric TEXT NOT NULL,
    metric_value REAL,
    threshold_value REAL,
    explanation TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_weather_timestamp ON weather_records(timestamp);
CREATE INDEX IF NOT EXISTS idx_adaptive_forecast_uuid ON adaptive_forecasts(forecast_uuid);
CREATE INDEX IF NOT EXISTS idx_adaptive_runs_date ON adaptive_optimization_runs(run_date);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON energy_alerts(is_active, severity);

-- ============================================================================
-- PHASE 9: EXPLAINABLE AI, MULTI-OBJECTIVE OPTIMIZATION & WHAT-IF TABLES
-- ============================================================================

-- 14. Decision Explanations Linked to Actual Optimization Results
CREATE TABLE IF NOT EXISTS decision_explanations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    explanation_uuid TEXT NOT NULL UNIQUE,
    run_uuid TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    summary_headline TEXT NOT NULL,
    detailed_explanation TEXT NOT NULL,
    key_metrics_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 15. Intelligent Optimization Recommendations
CREATE TABLE IF NOT EXISTS optimization_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rec_uuid TEXT NOT NULL UNIQUE,
    run_uuid TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('HIGH', 'MEDIUM', 'LOW')),
    explanation TEXT NOT NULL,
    expected_benefit TEXT,
    possible_drawback TEXT,
    evidence_level TEXT NOT NULL,
    supporting_metrics_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 16. Multi-Objective Optimization Runs
CREATE TABLE IF NOT EXISTS multi_objective_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_uuid TEXT NOT NULL UNIQUE,
    run_name TEXT NOT NULL,
    weights_json TEXT NOT NULL,
    expected_cost_inr REAL NOT NULL,
    cvar_95_inr REAL NOT NULL,
    solar_utilization_pct REAL NOT NULL,
    grid_dependency_pct REAL NOT NULL,
    battery_throughput_kwh REAL NOT NULL,
    degradation_cost_inr REAL NOT NULL,
    is_cost_only INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 17. Pareto Frontier Non-Dominated Solutions
CREATE TABLE IF NOT EXISTS pareto_solutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    solution_uuid TEXT NOT NULL UNIQUE,
    set_uuid TEXT NOT NULL,
    weights_json TEXT NOT NULL,
    expected_cost_inr REAL NOT NULL,
    cvar_95_inr REAL NOT NULL,
    solar_utilization_pct REAL NOT NULL,
    grid_dependency_pct REAL NOT NULL,
    battery_throughput_kwh REAL NOT NULL,
    degradation_cost_inr REAL NOT NULL,
    is_pareto_optimal INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 18. What-If Simulation Laboratory Experiments
CREATE TABLE IF NOT EXISTS what_if_experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_uuid TEXT NOT NULL UNIQUE,
    experiment_name TEXT NOT NULL,
    baseline_run_uuid TEXT,
    modified_params_json TEXT NOT NULL,
    expected_cost_inr REAL NOT NULL,
    baseline_cost_inr REAL,
    cost_delta_inr REAL,
    cvar_95_inr REAL NOT NULL,
    baseline_cvar_inr REAL,
    cvar_delta_inr REAL,
    vss_inr REAL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 19. Battery Degradation & Lifecycle Analytics
CREATE TABLE IF NOT EXISTS battery_lifecycle_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metrics_uuid TEXT NOT NULL UNIQUE,
    run_uuid TEXT NOT NULL,
    charge_throughput_kwh REAL NOT NULL,
    discharge_throughput_kwh REAL NOT NULL,
    equivalent_full_cycles REAL NOT NULL,
    avg_dod_pct REAL NOT NULL,
    max_dod_pct REAL NOT NULL,
    battery_utilization_pct REAL NOT NULL,
    estimated_degradation_cost_inr REAL NOT NULL,
    projected_cycle_life_remaining REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_explanations_run ON decision_explanations(run_uuid);
CREATE INDEX IF NOT EXISTS idx_recommendations_run ON optimization_recommendations(run_uuid);
CREATE INDEX IF NOT EXISTS idx_pareto_set ON pareto_solutions(set_uuid);
CREATE INDEX IF NOT EXISTS idx_whatif_exp ON what_if_experiments(experiment_uuid);
CREATE INDEX IF NOT EXISTS idx_battery_run ON battery_lifecycle_metrics(run_uuid);

-- ============================================================================
-- PHASE 10: USERS & RBAC SECURITY, BACKGROUND JOBS & HEALTH
-- ============================================================================

-- 20. User Authentication & Role-Based Access Control
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'operator', 'viewer')),
    full_name TEXT,
    email TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 21. Asynchronous Background Optimization Jobs
CREATE TABLE IF NOT EXISTS background_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_uuid TEXT NOT NULL UNIQUE,
    job_type TEXT NOT NULL DEFAULT 'STOCHASTIC_OPTIMIZATION',
    status TEXT NOT NULL CHECK(status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    params_json TEXT NOT NULL,
    result_json TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_jobs_uuid ON background_jobs(job_uuid);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON background_jobs(status);




