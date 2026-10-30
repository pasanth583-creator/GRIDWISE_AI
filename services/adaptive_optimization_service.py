"""
GRIDWISE AI - Adaptive Stochastic Optimization & Alerts Engine
Phase 8 Live Weather Ingestion, Adaptive Scenario Solving, Previous-Run Comparison,
and Automated Operational & Financial Alert Generation.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timezone
import uuid
import json
import logging
import numpy as np
import pandas as pd

from database.database import execute_db, query_db
from optimization import (
    StochasticOptimizer,
    BatteryParameters,
    GridParameters,
    OptimizationOutput,
)
from services.weather_service import WeatherService
from services.adaptive_forecasting_service import AdaptiveForecastingService

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ADAPTIVE_DIR = BASE_DIR / "data" / "adaptive"
ADAPTIVE_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_JSON = ADAPTIVE_DIR / "adaptive_optimization_results.json"
ALERTS_JSON = ADAPTIVE_DIR / "adaptive_alerts.json"


class AdaptiveAlertsEngine:
    """Evaluates multi-category operational and financial alerts with configurable thresholds."""

    # Configurable default thresholds
    THRESHOLDS = {
        "solar_reduction_kwh": 2600.0,       # Alert if mean daily solar < 2600 kWh (typical is ~3400)
        "demand_surge_kwh": 10500.0,         # Alert if daily demand > 10500 kWh
        "high_procurement_cost_inr": 56000.0,# Alert if expected cost > ₹56,000
        "critical_cost_inr": 60000.0,        # Critical alert if cost > ₹60,000
        "cvar_risk_inr": 61000.0,            # Alert if CVaR 95% > ₹61,000
        "procurement_shift_pct": 20.0,       # Alert if day-ahead commitment changes by > 20%
        "battery_min_headroom_kwh": 200.0,   # Minimum buffer reserve
    }

    @classmethod
    def evaluate_and_record_alerts(
        cls,
        stochastic_out: OptimizationOutput,
        summary_stats: Dict[str, Any],
        previous_run: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates conditions across 6 core categories and persists active alerts to SQLite.
        """
        alerts = []
        now_iso = datetime.now(timezone.utc).isoformat()

        mean_solar = summary_stats.get("mean_daily_solar_kwh", 3200.0)
        mean_demand = summary_stats.get("mean_daily_demand_kwh", 9600.0)
        exp_cost = stochastic_out.expected_total_cost_inr
        cvar_cost = stochastic_out.cvar_95_cost_inr
        da_total_kwh = float(np.sum(stochastic_out.day_ahead_schedule_kw))

        # 1. Solar Generation Reduction Alert
        if mean_solar < cls.THRESHOLDS["solar_reduction_kwh"]:
            alerts.append({
                "alert_uuid": f"ALT-SOLAR-{uuid.uuid4().hex[:6].upper()}",
                "category": "Solar Reduction",
                "severity": "WARNING" if mean_solar > 2000.0 else "CRITICAL",
                "triggering_metric": "mean_daily_solar_kwh",
                "metric_value": round(mean_solar, 1),
                "threshold_value": cls.THRESHOLDS["solar_reduction_kwh"],
                "explanation": f"Live weather forecasts indicate high cloud cover; projected solar PV generation is {mean_solar:.1f} kWh, below threshold {cls.THRESHOLDS['solar_reduction_kwh']} kWh.",
                "recommended_action": "Increase day-ahead grid procurement during off-peak hours and preserve battery storage for evening peak dispatch.",
                "timestamp": now_iso,
            })

        # 2. Campus Demand Surge Alert
        if mean_demand > cls.THRESHOLDS["demand_surge_kwh"]:
            alerts.append({
                "alert_uuid": f"ALT-DEM-{uuid.uuid4().hex[:6].upper()}",
                "category": "Demand Surge",
                "severity": "WARNING",
                "triggering_metric": "mean_daily_demand_kwh",
                "metric_value": round(mean_demand, 1),
                "threshold_value": cls.THRESHOLDS["demand_surge_kwh"],
                "explanation": f"Elevated ambient temperatures and humidity are driving HVAC chiller loads up to {mean_demand:.1f} kWh.",
                "recommended_action": "Verify campus demand-response readiness and pre-cool facilities during low-tariff morning hours.",
                "timestamp": now_iso,
            })

        # 3. High Procurement Cost Alert
        if exp_cost > cls.THRESHOLDS["critical_cost_inr"]:
            alerts.append({
                "alert_uuid": f"ALT-COST-{uuid.uuid4().hex[:6].upper()}",
                "category": "High Cost",
                "severity": "CRITICAL",
                "triggering_metric": "expected_cost_inr",
                "metric_value": round(exp_cost, 2),
                "threshold_value": cls.THRESHOLDS["critical_cost_inr"],
                "explanation": f"Optimal daily electricity procurement cost projected at ₹{exp_cost:,.2f}, exceeding critical limit of ₹{cls.THRESHOLDS['critical_cost_inr']:,.2f}.",
                "recommended_action": "Enforce microgrid load shedding on non-essential campus feeders or shift scheduled battery discharge to coincide with peak spot tariff hours.",
                "timestamp": now_iso,
            })
        elif exp_cost > cls.THRESHOLDS["high_procurement_cost_inr"]:
            alerts.append({
                "alert_uuid": f"ALT-COST-{uuid.uuid4().hex[:6].upper()}",
                "category": "High Cost",
                "severity": "WARNING",
                "triggering_metric": "expected_cost_inr",
                "metric_value": round(exp_cost, 2),
                "threshold_value": cls.THRESHOLDS["high_procurement_cost_inr"],
                "explanation": f"Projected daily procurement cost is ₹{exp_cost:,.2f}, above warning threshold ₹{cls.THRESHOLDS['high_procurement_cost_inr']:,.2f}.",
                "recommended_action": "Monitor real-time balancing tariffs and utilize battery discharge to curtail grid import spikes.",
                "timestamp": now_iso,
            })

        # 4. Tail Risk / CVaR Alert
        if cvar_cost > cls.THRESHOLDS["cvar_risk_inr"]:
            alerts.append({
                "alert_uuid": f"ALT-CVAR-{uuid.uuid4().hex[:6].upper()}",
                "category": "CVaR Risk",
                "severity": "WARNING",
                "triggering_metric": "cvar_95_inr",
                "metric_value": round(cvar_cost, 2),
                "threshold_value": cls.THRESHOLDS["cvar_risk_inr"],
                "explanation": f"95% Conditional Value at Risk is ₹{cvar_cost:,.2f}, indicating heightened risk of costly real-time balancing shortages under adverse weather scenarios.",
                "recommended_action": "Increase optimization risk aversion parameter (lambda >= 0.2) to hedge worst-case scenario outcomes.",
                "timestamp": now_iso,
            })

        # 5. Battery Readiness / Health Check
        min_soc_seen = float(np.min(stochastic_out.expected_battery_soc_kwh))
        if min_soc_seen < cls.THRESHOLDS["battery_min_headroom_kwh"]:
            alerts.append({
                "alert_uuid": f"ALT-BATT-{uuid.uuid4().hex[:6].upper()}",
                "category": "Battery Readiness",
                "severity": "INFO",
                "triggering_metric": "min_soc_kwh",
                "metric_value": round(min_soc_seen, 1),
                "threshold_value": cls.THRESHOLDS["battery_min_headroom_kwh"],
                "explanation": f"Expected battery storage reaches minimum buffer of {min_soc_seen:.1f} kWh (near 15% reserve limit).",
                "recommended_action": "Ensure scheduled battery recharging occurs during early morning off-peak window.",
                "timestamp": now_iso,
            })

        # 6. Grid Procurement Shift vs Previous Run
        if previous_run and "day_ahead_energy_kwh" in previous_run:
            prev_da = float(previous_run["day_ahead_energy_kwh"])
            if prev_da > 0:
                shift_pct = abs(da_total_kwh - prev_da) / prev_da * 100.0
                if shift_pct > cls.THRESHOLDS["procurement_shift_pct"]:
                    alerts.append({
                        "alert_uuid": f"ALT-SHIFT-{uuid.uuid4().hex[:6].upper()}",
                        "category": "Grid Procurement Change",
                        "severity": "INFO",
                        "triggering_metric": "procurement_shift_pct",
                        "metric_value": round(shift_pct, 1),
                        "threshold_value": cls.THRESHOLDS["procurement_shift_pct"],
                        "explanation": f"Day-ahead grid procurement recommendation shifted by {shift_pct:.1f}% ({da_total_kwh:.1f} kWh vs {prev_da:.1f} kWh in previous run) due to live weather updates.",
                        "recommended_action": "Review updated hourly dispatch schedule before submitting final day-ahead bids to the utility.",
                        "timestamp": now_iso,
                    })

        # Save to SQLite table energy_alerts
        try:
            for alt in alerts:
                execute_db(
                    """
                    INSERT OR REPLACE INTO energy_alerts (
                        alert_uuid, category, severity, triggering_metric,
                        metric_value, threshold_value, explanation,
                        recommended_action, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        alt["alert_uuid"], alt["category"], alt["severity"],
                        alt["triggering_metric"], alt["metric_value"],
                        alt["threshold_value"], alt["explanation"],
                        alt["recommended_action"]
                    ),
                )
        except Exception as e:
            logger.warning(f"Could not persist alerts to DB: {e}")

        # Save to JSON file
        try:
            with open(ALERTS_JSON, "w", encoding="utf-8") as f:
                json.dump(alerts, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving alerts JSON: {e}")

        return alerts


class AdaptiveOptimizationService:
    """Coordinates end-to-end adaptive optimization conditioned on live weather scenarios."""

    @classmethod
    def run_adaptive_optimization(
        cls,
        num_scenarios: int = 100,
        risk_aversion_lambda: float = 0.0,
        battery_capacity_kwh: float = 1000.0,
        initial_soc_pct: float = 0.50,
        force_weather_refresh: bool = False,
        random_seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Full Phase 8 adaptive execution workflow:
        1. Ingest live weather.
        2. Generate weather-adapted forecasts.
        3. Generate >= 100 adaptive scenarios.
        4. Validate scenarios.
        5. Solve Two-Stage Stochastic LP (SciPy HiGHS).
        6. Calculate expected cost, VaR, CVaR.
        7. Compute comparison deltas against previous run.
        8. Evaluate operational alerts.
        9. Persist complete run history.
        """
        logger.info(f"Running Adaptive Optimization: N={num_scenarios}, lambda={risk_aversion_lambda}")

        # 1-3. Generate fresh live-weather-conditioned scenarios
        if force_weather_refresh:
            WeatherService.refresh_weather()

        summary_stats = AdaptiveForecastingService.generate_adaptive_scenarios(
            num_scenarios=num_scenarios,
            random_seed=random_seed,
        )

        # 4. Load & Validate Adaptive Scenarios
        scen_csv = ADAPTIVE_DIR / "adaptive_scenarios.csv"
        if not scen_csv.exists():
            raise FileNotFoundError("Adaptive scenarios CSV could not be located.")

        df_scenarios = pd.read_csv(scen_csv)
        unique_ids = df_scenarios["scenario_id"].unique()
        if len(unique_ids) < num_scenarios:
            logger.warning(f"Scenario count ({len(unique_ids)}) less than requested ({num_scenarios}).")

        # Validation assertions
        assert not df_scenarios.empty, "Scenarios DataFrame is empty"
        assert len(df_scenarios) % 24 == 0, "Scenario records must be multiples of 24 hours"
        assert np.all(df_scenarios["demand_kwh"] >= 0), "Demand must be non-negative"
        assert np.all(df_scenarios["solar_kwh"] >= 0), "Solar must be non-negative"
        assert np.all(df_scenarios["solar_kwh"] <= 800.0), "Solar must not exceed capacity"
        assert np.all(df_scenarios["day_ahead_price_inr_kwh"] > 0), "DA prices must be positive"

        # 5. Configure Microgrid Model
        battery = BatteryParameters(
            capacity_kwh=battery_capacity_kwh,
            max_charge_kw=400.0,
            max_discharge_kw=400.0,
            initial_soc_pct=initial_soc_pct,
            charging_efficiency=0.92,
            discharging_efficiency=0.92,
        )
        grid = GridParameters(
            max_day_ahead_import_kw=1000.0,
            max_real_time_import_kw=1000.0,
            max_total_import_kw=1000.0,
            max_export_kw=500.0,
        )

        optimizer = StochasticOptimizer(battery_params=battery, grid_params=grid)

        # 6. Solve Two-Stage Stochastic Program (SciPy HiGHS)
        stochastic_out = optimizer.solve_stochastic_model(
            scenarios_df=df_scenarios,
            risk_weight_lambda=risk_aversion_lambda,
        )

        # 7. Solve Deterministic Baseline & EVPI
        x_det, eev_cost, ev_obj, diag = optimizer.solve_deterministic_baseline(df_scenarios)
        vss_val = max(0.0, eev_cost - stochastic_out.expected_total_cost_inr)
        vss_pct = (vss_val / eev_cost * 100.0) if eev_cost > 0 else 0.0

        ws_cost, _ = optimizer.solve_wait_and_see(df_scenarios)
        evpi_val = max(0.0, stochastic_out.expected_total_cost_inr - ws_cost)

        # 8. Retrieve Previous Run for Comparison
        previous_run = cls.get_latest_adaptive_results()
        cost_delta = 0.0
        cvar_delta = 0.0
        prev_run_uuid = None

        if previous_run:
            prev_run_uuid = previous_run.get("run_uuid")
            prev_cost = previous_run.get("expected_cost_inr", 0.0)
            prev_cvar = previous_run.get("cvar_95_inr", 0.0)
            cost_delta = round(stochastic_out.expected_total_cost_inr - prev_cost, 2)
            cvar_delta = round(stochastic_out.cvar_95_cost_inr - prev_cvar, 2)

        # 9. Evaluate Operational Alerts
        active_alerts = AdaptiveAlertsEngine.evaluate_and_record_alerts(
            stochastic_out=stochastic_out,
            summary_stats=summary_stats,
            previous_run=previous_run,
        )

        # 10. Format Result Payload
        run_uuid = f"ADAPT-RUN-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()
        now_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        total_da_energy = float(np.sum(stochastic_out.day_ahead_schedule_kw))
        total_rt_energy = float(np.sum(stochastic_out.expected_real_time_import_kw))
        total_battery_cycled = float(np.sum(stochastic_out.expected_battery_discharge_kw))

        results_payload = {
            "run_uuid": run_uuid,
            "run_name": f"Adaptive Weather Optimization (N={len(unique_ids)}, λ={risk_aversion_lambda})",
            "run_date": now_date,
            "created_at": now_iso,
            "solver_status": "OPTIMAL" if stochastic_out.success else "FAILED",
            "solver_name": "SciPy HiGHS LP Solver",
            "solve_time_sec": round(stochastic_out.solve_time_sec, 3),
            "num_scenarios": len(unique_ids),
            "expected_cost_inr": round(stochastic_out.expected_total_cost_inr, 2),
            "eev_deterministic_cost_inr": round(eev_cost, 2),
            "vss_inr": round(vss_val, 2),
            "vss_pct": round(vss_pct, 2),
            "ws_cost_inr": round(ws_cost, 2),
            "evpi_inr": round(evpi_val, 2),
            "var_95_inr": round(stochastic_out.var_95_cost_inr, 2),
            "cvar_95_inr": round(stochastic_out.cvar_95_cost_inr, 2),
            "std_cost_inr": round(stochastic_out.std_scenario_cost_inr, 2),
            "day_ahead_energy_kwh": round(total_da_energy, 1),
            "expected_real_time_energy_kwh": round(total_rt_energy, 1),
            "battery_cycled_kwh": round(total_battery_cycled, 1),
            "comparison": {
                "previous_run_uuid": prev_run_uuid,
                "cost_delta_inr": cost_delta,
                "cvar_delta_inr": cvar_delta,
                "cost_change_pct": round(cost_delta / prev_cost * 100.0, 2) if (previous_run and prev_cost > 0) else 0.0,
            },
            "alerts": active_alerts,
            "hourly_schedule": {
                "hour": list(range(24)),
                "day_ahead_procurement_kw": [round(float(v), 2) for v in stochastic_out.day_ahead_schedule_kw],
                "expected_real_time_kw": [round(float(v), 2) for v in stochastic_out.expected_real_time_import_kw],
                "expected_battery_charge_kw": [round(float(v), 2) for v in stochastic_out.expected_battery_charge_kw],
                "expected_battery_discharge_kw": [round(float(v), 2) for v in stochastic_out.expected_battery_discharge_kw],
                "expected_soc_kwh": [round(float(v), 2) for v in stochastic_out.expected_battery_soc_kwh],
                "expected_export_kw": [round(float(v), 2) for v in stochastic_out.expected_export_kw],
            },
        }

        # Save to JSON
        try:
            with open(RESULTS_JSON, "w", encoding="utf-8") as f:
                json.dump(results_payload, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving adaptive optimization results JSON: {e}")

        # Persist to SQLite table adaptive_optimization_runs
        try:
            execute_db(
                """
                INSERT INTO adaptive_optimization_runs (
                    run_uuid, run_name, run_date, data_source,
                    num_scenarios, expected_cost_inr, var_95_inr, cvar_95_inr,
                    vss_inr, vss_pct, previous_run_uuid, cost_delta_inr, cvar_delta_inr,
                    solver_status, solve_time_sec, day_ahead_schedule_json, battery_dispatch_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_uuid,
                    results_payload["run_name"],
                    now_date,
                    "Open-Meteo Live API + Adaptive Stochastic Engine",
                    len(unique_ids),
                    results_payload["expected_cost_inr"],
                    results_payload["var_95_inr"],
                    results_payload["cvar_95_inr"],
                    results_payload["vss_inr"],
                    results_payload["vss_pct"],
                    prev_run_uuid,
                    cost_delta,
                    cvar_delta,
                    results_payload["solver_status"],
                    results_payload["solve_time_sec"],
                    json.dumps(results_payload["hourly_schedule"]["day_ahead_procurement_kw"]),
                    json.dumps(results_payload["hourly_schedule"]["expected_soc_kwh"]),
                ),
            )
        except Exception as e:
            logger.warning(f"Could not persist adaptive run to SQLite: {e}")

        return results_payload

    @classmethod
    def get_latest_adaptive_results(cls) -> Optional[Dict[str, Any]]:
        """Reads latest adaptive optimization results from disk."""
        if RESULTS_JSON.exists():
            try:
                with open(RESULTS_JSON, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading adaptive optimization results: {e}")
        return None

    @classmethod
    def get_adaptive_history(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """Queries historical adaptive optimization runs from SQLite."""
        try:
            rows = query_db(
                """
                SELECT run_uuid, run_name, run_date, num_scenarios,
                       expected_cost_inr, var_95_inr, cvar_95_inr, vss_inr,
                       vss_pct, cost_delta_inr, solver_status, solve_time_sec, created_at
                FROM adaptive_optimization_runs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error querying adaptive history: {e}")
            return []

    @classmethod
    def get_active_alerts(cls) -> List[Dict[str, Any]]:
        """Queries active alerts from SQLite or falls back to JSON cache."""
        try:
            rows = query_db(
                """
                SELECT alert_uuid, category, severity, triggering_metric,
                       metric_value, threshold_value, explanation,
                       recommended_action, created_at
                FROM energy_alerts
                WHERE is_active = 1
                ORDER BY CASE severity
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'WARNING' THEN 2
                    WHEN 'INFO' THEN 3
                    ELSE 4 END, created_at DESC
                LIMIT 20
                """
            )
            if rows:
                return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"Could not query alerts from DB: {e}")

        if ALERTS_JSON.exists():
            try:
                with open(ALERTS_JSON, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

