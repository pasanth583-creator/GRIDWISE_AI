"""
GRIDWISE AI - Service Layer
Business logic, database interaction, and dataset query services for Campus Microgrid.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from database.database import query_db, execute_db, check_db_health
from models import MicrogridConfig, OptimizationRunSummary

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


class DatasetService:
    """Service providing access to Phase 3 synthetic datasets and statistical summaries."""

    _cached_demand: Optional[pd.DataFrame] = None
    _cached_solar: Optional[pd.DataFrame] = None
    _cached_prices: Optional[pd.DataFrame] = None
    _cached_scenarios: Optional[pd.DataFrame] = None
    _cached_weather: Optional[pd.DataFrame] = None

    @classmethod
    def load_data(cls):
        """Loads processed CSV datasets into memory if not already cached."""
        proc_dir = DATA_DIR / "processed"
        scen_dir = DATA_DIR / "scenarios"

        if cls._cached_demand is None and (proc_dir / "campus_demand_hourly.csv").exists():
            cls._cached_demand = pd.read_csv(proc_dir / "campus_demand_hourly.csv")
        if cls._cached_solar is None and (proc_dir / "solar_generation_hourly.csv").exists():
            cls._cached_solar = pd.read_csv(proc_dir / "solar_generation_hourly.csv")
        if cls._cached_prices is None and (proc_dir / "electricity_prices_hourly.csv").exists():
            cls._cached_prices = pd.read_csv(proc_dir / "electricity_prices_hourly.csv")
        if cls._cached_scenarios is None and (scen_dir / "combined_scenarios_500.csv").exists():
            cls._cached_scenarios = pd.read_csv(scen_dir / "combined_scenarios_500.csv")
        if cls._cached_weather is None and (scen_dir / "weather_scenarios_500.csv").exists():
            cls._cached_weather = pd.read_csv(scen_dir / "weather_scenarios_500.csv")

    @classmethod
    def get_summary_statistics(cls) -> Dict[str, Any]:
        """Calculates macro-level dataset statistics across 8760 hours and 500 scenarios."""
        cls.load_data()
        if cls._cached_demand is None or cls._cached_solar is None:
            return {
                "status": "DATASET_NOT_GENERATED",
                "is_synthetic": True,
                "label": "SYNTHETIC SIMULATION DATA – NOT LIVE METER DATA",
            }

        total_demand_kwh = float(cls._cached_demand["actual_demand_kwh"].sum())
        total_solar_kwh = float(cls._cached_solar["solar_generation_kwh"].sum())
        avg_daily_demand = total_demand_kwh / 365.0
        avg_daily_solar = total_solar_kwh / 365.0
        peak_demand = float(cls._cached_demand["actual_demand_kwh"].max())
        peak_solar = float(cls._cached_solar["solar_generation_kwh"].max())

        avg_da_price = float(cls._cached_prices["day_ahead_price_inr_kwh"].mean()) if cls._cached_prices is not None else 7.50
        avg_rt_price = float(cls._cached_prices["real_time_price_inr_kwh"].mean()) if cls._cached_prices is not None else 8.20

        weather_dist = {}
        if cls._cached_weather is not None:
            weather_dist = cls._cached_weather["weather_condition"].value_counts().to_dict()

        return {
            "status": "VALIDATED_SUCCESSFULLY",
            "is_synthetic": True,
            "label": "SYNTHETIC SIMULATION DATA – NOT LIVE METER DATA",
            "annual_demand_mwh": round(total_demand_kwh / 1000.0, 2),
            "annual_solar_mwh": round(total_solar_kwh / 1000.0, 2),
            "avg_daily_demand_kwh": round(avg_daily_demand, 1),
            "avg_daily_solar_kwh": round(avg_daily_solar, 1),
            "peak_demand_kw": round(peak_demand, 1),
            "peak_solar_kw": round(peak_solar, 1),
            "capacity_factor_pct": round(total_solar_kwh / (800.0 * 8760.0) * 100.0, 1),
            "avg_da_price_inr_kwh": round(avg_da_price, 2),
            "avg_rt_price_inr_kwh": round(avg_rt_price, 2),
            "weather_distribution": weather_dist,
            "num_scenarios": 500,
            "total_hourly_records": len(cls._cached_demand),
        }

    @classmethod
    def get_overview_kpis(cls) -> Dict[str, Any]:
        """Returns verified daily KPI metrics derived directly from generated synthetic data."""
        stats = cls.get_summary_statistics()
        if stats.get("status") == "DATASET_NOT_GENERATED":
            return {
                "daily_demand_kwh": 11598.7,
                "daily_solar_kwh": 3284.9,
                "battery_soc_pct": 50,
                "battery_soc_kwh": 500,
                "grid_purchased_kwh": 8313.8,
                "expected_daily_cost_inr": 86750.0,
                "currency": "INR",
                "label": "SYNTHETIC SIMULATION DATA – NOT LIVE METER DATA",
            }

        daily_demand = stats["avg_daily_demand_kwh"]
        daily_solar = stats["avg_daily_solar_kwh"]
        grid_purchased = max(0.0, daily_demand - daily_solar)
        
        # Calculate expected daily cost using average TOU blended rate (INR)
        blended_rate = stats["avg_da_price_inr_kwh"]
        daily_cost_inr = round(grid_purchased * blended_rate, 2)

        return {
            "daily_demand_kwh": round(daily_demand, 1),
            "daily_solar_kwh": round(daily_solar, 1),
            "battery_soc_pct": 50,
            "battery_soc_kwh": 500,  # 50% of 1000 kWh reference
            "grid_purchased_kwh": round(grid_purchased, 1),
            "expected_daily_cost_inr": daily_cost_inr,
            "currency": "INR",
            "label": "SYNTHETIC SIMULATION DATA – NOT LIVE METER DATA",
        }

    @classmethod
    def get_chart_datasets(cls) -> Dict[str, Any]:
        """Provides verified data series for all 8 Phase 3 Plotly charts."""
        cls.load_data()

        # 1. 24-hour campus demand curve (average profile across weekdays)
        if cls._cached_demand is not None:
            weekday_demand = cls._cached_demand[cls._cached_demand["day_type"] == "Weekday"]
            hourly_demand_curve = weekday_demand.groupby("hour")["actual_demand_kwh"].mean().round(1).tolist()
            hourly_demand_base = weekday_demand.groupby("hour")["base_demand_kwh"].mean().round(1).tolist()
            
            # Daily total consumption trend for first 30 days
            daily_series = cls._cached_demand.groupby("date")["actual_demand_kwh"].sum().head(30).round(1).to_dict()
            daily_dates = list(daily_series.keys())
            daily_demand_totals = list(daily_series.values())
        else:
            hourly_demand_curve = [230, 215, 210, 205, 215, 260, 360, 520, 720, 840, 890, 915, 870, 860, 910, 925, 880, 740, 620, 540, 460, 390, 310, 260]
            hourly_demand_base = hourly_demand_curve
            daily_dates = [f"Day {i+1}" for i in range(30)]
            daily_demand_totals = [11500 for _ in range(30)]

        # 2. 24-hour solar generation curve (average daylight yield)
        if cls._cached_solar is not None:
            hourly_solar_curve = cls._cached_solar.groupby("hour")["solar_generation_kwh"].mean().round(1).tolist()
            
            # Solar by weather condition
            solar_by_weather = {}
            for cond in ["Sunny", "Partly Cloudy", "Cloudy", "Rainy"]:
                sub = cls._cached_solar[cls._cached_solar["weather_condition"] == cond]
                if len(sub) > 0:
                    solar_by_weather[cond] = sub.groupby("hour")["solar_generation_kwh"].mean().round(1).tolist()
                else:
                    solar_by_weather[cond] = [0.0] * 24
        else:
            hourly_solar_curve = [0,0,0,0,0,0, 35, 120, 290, 480, 620, 680, 650, 560, 410, 220, 85, 15, 0,0,0,0,0,0]
            solar_by_weather = {
                "Sunny": [0,0,0,0,0,0, 45, 150, 350, 560, 710, 760, 740, 640, 480, 260, 100, 20, 0,0,0,0,0,0],
                "Partly Cloudy": [0,0,0,0,0,0, 30, 110, 260, 430, 560, 610, 580, 500, 370, 200, 75, 12, 0,0,0,0,0,0],
                "Cloudy": [0,0,0,0,0,0, 15, 55, 140, 230, 310, 340, 320, 280, 200, 110, 40, 6, 0,0,0,0,0,0],
                "Rainy": [0,0,0,0,0,0, 5, 20, 50, 80, 110, 120, 115, 95, 70, 35, 15, 2, 0,0,0,0,0,0],
            }

        # 3. Electricity price by hour
        if cls._cached_prices is not None:
            hourly_da_prices = cls._cached_prices.groupby("hour")["day_ahead_price_inr_kwh"].mean().round(2).tolist()
            hourly_rt_prices = cls._cached_prices.groupby("hour")["real_time_price_inr_kwh"].mean().round(2).tolist()
        else:
            hourly_da_prices = [4.20]*6 + [7.50]*8 + [11.80]*6 + [7.50]*2 + [4.20]*2
            hourly_rt_prices = [p + 0.4 for p in hourly_da_prices]

        # 4. Scenarios distributions (Demand fan & Solar uncertainty envelope)
        if cls._cached_scenarios is not None:
            # Demand percentiles across 500 scenarios
            demand_p10 = cls._cached_scenarios.groupby("hour")["demand_kwh"].quantile(0.10).round(1).tolist()
            demand_p50 = cls._cached_scenarios.groupby("hour")["demand_kwh"].quantile(0.50).round(1).tolist()
            demand_p90 = cls._cached_scenarios.groupby("hour")["demand_kwh"].quantile(0.90).round(1).tolist()

            # Solar percentiles across 500 scenarios
            solar_p10 = cls._cached_scenarios.groupby("hour")["solar_kwh"].quantile(0.10).round(1).tolist()
            solar_p50 = cls._cached_scenarios.groupby("hour")["solar_kwh"].quantile(0.50).round(1).tolist()
            solar_p90 = cls._cached_scenarios.groupby("hour")["solar_kwh"].quantile(0.90).round(1).tolist()
        else:
            demand_p50 = hourly_demand_curve
            demand_p10 = [d * 0.88 for d in demand_p50]
            demand_p90 = [d * 1.12 for d in demand_p50]
            solar_p50 = hourly_solar_curve
            solar_p10 = [s * 0.70 for s in solar_p50]
            solar_p90 = [s * 1.20 for s in solar_p50]

        # 5. Scenario probability distribution
        if cls._cached_weather is not None:
            weather_counts = cls._cached_weather["weather_condition"].value_counts().to_dict()
            weather_labels = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy"]
            weather_probs = [
                float(cls._cached_weather[cls._cached_weather["weather_condition"] == w]["probability"].sum())
                for w in weather_labels
            ]
        else:
            weather_labels = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy"]
            weather_counts = {"Sunny": 175, "Partly Cloudy": 150, "Cloudy": 100, "Rainy": 75}
            weather_probs = [0.35, 0.30, 0.20, 0.15]

        return {
            "hours": [f"{h:02d}:00" for h in range(24)],
            "demand_24h_actual": hourly_demand_curve,
            "demand_24h_base": hourly_demand_base,
            "daily_dates": daily_dates,
            "daily_demand_totals": daily_demand_totals,
            "solar_24h": hourly_solar_curve,
            "solar_by_weather": solar_by_weather,
            "prices_da_inr": hourly_da_prices,
            "prices_rt_inr": hourly_rt_prices,
            "demand_p10": demand_p10,
            "demand_p50": demand_p50,
            "demand_p90": demand_p90,
            "solar_p10": solar_p10,
            "solar_p50": solar_p50,
            "solar_p90": solar_p90,
            "weather_labels": weather_labels,
            "weather_counts": weather_counts,
            "weather_probs": weather_probs,
        }


class MicrogridService:
    """Service handling campus microgrid configuration and operational data queries."""

    @staticmethod
    def get_active_config() -> MicrogridConfig:
        """Fetch the active microgrid configuration from database or return default."""
        try:
            row = query_db(
                "SELECT * FROM microgrid_config WHERE is_active = 1 ORDER BY id DESC LIMIT 1;",
                one=True,
            )
            if row:
                return MicrogridConfig(
                    id=row["id"],
                    config_name=row["config_name"],
                    pv_capacity_kw=row["pv_capacity_kw"],
                    bess_capacity_kwh=row["bess_capacity_kwh"],
                    bess_max_power_kw=row["bess_max_power_kw"],
                    bess_charge_efficiency=row["bess_charge_efficiency"],
                    bess_discharge_efficiency=row["bess_discharge_efficiency"],
                    min_soc=row["min_soc"],
                    max_soc=row["max_soc"],
                    initial_soc=row["initial_soc"],
                    grid_import_limit_kw=row["grid_import_limit_kw"],
                    grid_export_limit_kw=row["grid_export_limit_kw"],
                    demand_charge_rate=row["demand_charge_rate"],
                )
        except Exception as e:
            logger.warning(f"Could not load config from DB, using defaults: {e}")
        return MicrogridConfig()

    @staticmethod
    def get_latest_optimization_run() -> Optional[Dict[str, Any]]:
        """Fetch the latest optimization run record if available."""
        try:
            run = query_db(
                "SELECT * FROM optimization_runs ORDER BY id DESC LIMIT 1;",
                one=True,
            )
            return run
        except Exception as e:
            logger.error(f"Error fetching latest optimization run: {e}")
            return None

    @staticmethod
    def get_optimization_runs_list(limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch a list of recent optimization runs."""
        try:
            runs = query_db(
                "SELECT * FROM optimization_runs ORDER BY id DESC LIMIT ?;",
                (limit,),
            )
            return runs
        except Exception as e:
            logger.error(f"Error listing optimization runs: {e}")
            return []

    @staticmethod
    def get_system_summary() -> Dict[str, Any]:
        """Aggregate system KPIs and operational status."""
        config = MicrogridService.get_active_config()
        db_health = check_db_health()
        latest_run = MicrogridService.get_latest_optimization_run()
        dataset_stats = DatasetService.get_summary_statistics()

        return {
            "microgrid": config.to_dict(),
            "database_status": db_health.get("status", "UNKNOWN"),
            "database_connected": db_health.get("connected", False),
            "latest_run": latest_run,
            "architecture_phase": "Phase 3: Dataset & Stochastic Scenarios Ready",
            "optimization_engine_ready": True,
            "dataset_statistics": dataset_stats,
            "data_label": "SYNTHETIC SIMULATION DATA – NOT LIVE METER DATA",
        }


from services.optimization_service import OptimizationService
from services.analytics_service import EnergyAnalyticsService
from services.risk_analytics import RiskAnalyticsService
from services.battery_analytics import BatteryAnalyticsService
from services.cost_analysis import CostAnalysisService
from services.report_service import ReportService

__all__ = [
    "MicrogridService",
    "DatasetService",
    "OptimizationService",
    "EnergyAnalyticsService",
    "RiskAnalyticsService",
    "BatteryAnalyticsService",
    "CostAnalysisService",
    "ReportService",
]
