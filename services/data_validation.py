"""
GRIDWISE AI - Dataset Validation Engine
Automated integrity and physical constraint verification for Phase 3 synthetic data.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np


def _sanitize_for_json(obj: Any) -> Any:
    """Recursively converts NumPy types into native Python types for clean JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(x) for x in obj]
    elif isinstance(obj, (np.bool_, np.generic)):
        return obj.item()
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    return obj


class DatasetValidator:
    """
    Validates synthetic energy datasets and stochastic scenarios against strict physical and statistical rules.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.processed_dir = self.data_dir / "processed"
        self.scenarios_dir = self.data_dir / "scenarios"
        self.reports_dir = self.data_dir / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def validate_demand(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate 8760-hour campus electricity demand dataset."""
        checks = {}
        issues = []

        # 1. Exactly 8760 records
        record_count = len(df)
        checks["record_count_is_8760"] = (record_count == 8760)
        if record_count != 8760:
            issues.append(f"Expected 8760 records, found {record_count}")

        # 2. No missing timestamps
        missing_ts = df["timestamp"].isna().sum()
        checks["no_missing_timestamps"] = (missing_ts == 0)
        if missing_ts > 0:
            issues.append(f"Found {missing_ts} missing timestamps")

        # 3. No duplicate timestamps
        dup_ts = df["timestamp"].duplicated().sum()
        checks["no_duplicate_timestamps"] = (dup_ts == 0)
        if dup_ts > 0:
            issues.append(f"Found {dup_ts} duplicate timestamps")

        # 4. No negative demand
        neg_demand = (df["actual_demand_kwh"] < 0).sum()
        checks["no_negative_demand"] = (neg_demand == 0)
        if neg_demand > 0:
            issues.append(f"Found {neg_demand} negative demand values")

        # Basic statistics
        stats = {
            "min_demand_kwh": float(df["actual_demand_kwh"].min()),
            "max_demand_kwh": float(df["actual_demand_kwh"].max()),
            "mean_demand_kwh": float(df["actual_demand_kwh"].mean()),
            "total_annual_demand_mwh": float(df["actual_demand_kwh"].sum() / 1000.0),
        }

        passed = all(checks.values())
        return {
            "dataset": "campus_demand",
            "passed": passed,
            "checks": checks,
            "statistics": stats,
            "issues": issues,
        }

    def validate_solar(self, df: pd.DataFrame, max_capacity_kwp: float = 800.0) -> Dict[str, Any]:
        """Validate 8760-hour solar generation dataset."""
        checks = {}
        issues = []

        # 1. Exactly 8760 records
        record_count = len(df)
        checks["record_count_is_8760"] = (record_count == 8760)
        if record_count != 8760:
            issues.append(f"Expected 8760 records, found {record_count}")

        # 2. No missing timestamps
        missing_ts = df["timestamp"].isna().sum()
        checks["no_missing_timestamps"] = (missing_ts == 0)

        # 3. No duplicate timestamps
        dup_ts = df["timestamp"].duplicated().sum()
        checks["no_duplicate_timestamps"] = (dup_ts == 0)

        # 4. No negative solar generation
        neg_solar = (df["solar_generation_kwh"] < 0).sum()
        checks["no_negative_solar"] = (neg_solar == 0)
        if neg_solar > 0:
            issues.append(f"Found {neg_solar} negative solar values")

        # 5. Solar generation is strictly zero at night (hour < 6 or hour >= 19)
        night_solar = df[df["hour"].isin([20, 21, 22, 23, 0, 1, 2, 3, 4, 5])]["solar_generation_kwh"]
        night_nonzero = (night_solar > 0.0).sum()
        checks["solar_zero_at_night"] = (night_nonzero == 0)
        if night_nonzero > 0:
            issues.append(f"Found {night_nonzero} nocturnal hours with positive solar generation")

        # 6. Does not exceed installed capacity
        over_cap = (df["solar_generation_kwh"] > (max_capacity_kwp + 1e-3)).sum()
        checks["solar_within_capacity"] = (over_cap == 0)
        if over_cap > 0:
            issues.append(f"Found {over_cap} records exceeding installed capacity of {max_capacity_kwp} kWp")

        stats = {
            "max_solar_output_kwh": float(df["solar_generation_kwh"].max()),
            "mean_daylight_solar_kwh": float(df[df["hour"].between(6, 18)]["solar_generation_kwh"].mean()),
            "total_annual_generation_mwh": float(df["solar_generation_kwh"].sum() / 1000.0),
            "capacity_factor_pct": float(df["solar_generation_kwh"].sum() / (max_capacity_kwp * 8760.0) * 100.0),
        }

        passed = all(checks.values())
        return {
            "dataset": "solar_generation",
            "passed": passed,
            "checks": checks,
            "statistics": stats,
            "issues": issues,
        }

    def validate_prices(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate 8760-hour electricity price dataset."""
        checks = {}
        issues = []

        # 1. Exactly 8760 records
        record_count = len(df)
        checks["record_count_is_8760"] = (record_count == 8760)

        # 2. No missing timestamps
        checks["no_missing_timestamps"] = (df["timestamp"].isna().sum() == 0)

        # 3. No duplicate timestamps
        checks["no_duplicate_timestamps"] = (df["timestamp"].duplicated().sum() == 0)

        # 4. All prices are strictly positive
        da_pos = (df["day_ahead_price_inr_kwh"] > 0).all()
        rt_pos = (df["real_time_price_inr_kwh"] > 0).all()
        checks["day_ahead_prices_positive"] = bool(da_pos)
        checks["real_time_prices_positive"] = bool(rt_pos)
        if not (da_pos and rt_pos):
            issues.append("Found non-positive electricity prices")

        stats = {
            "mean_day_ahead_inr_kwh": float(df["day_ahead_price_inr_kwh"].mean()),
            "min_day_ahead_inr_kwh": float(df["day_ahead_price_inr_kwh"].min()),
            "max_day_ahead_inr_kwh": float(df["day_ahead_price_inr_kwh"].max()),
            "mean_real_time_inr_kwh": float(df["real_time_price_inr_kwh"].mean()),
            "max_real_time_inr_kwh": float(df["real_time_price_inr_kwh"].max()),
        }

        passed = all(checks.values())
        return {
            "dataset": "electricity_prices",
            "passed": passed,
            "checks": checks,
            "statistics": stats,
            "issues": issues,
        }

    def validate_scenarios(self, df_weather: pd.DataFrame, df_combined: pd.DataFrame) -> Dict[str, Any]:
        """Validate weather scenarios and 24-hr combined scenarios."""
        checks = {}
        issues = []

        # 1. Exactly 500 weather scenarios exist
        weather_count = len(df_weather)
        checks["exactly_500_weather_scenarios"] = (weather_count == 500)
        if weather_count != 500:
            issues.append(f"Expected 500 weather scenarios, got {weather_count}")

        # 2. Probabilities sum to 1.0
        prob_sum = float(df_weather["probability"].sum())
        checks["weather_probabilities_sum_to_one"] = bool(np.isclose(prob_sum, 1.0, atol=1e-5))
        if not checks["weather_probabilities_sum_to_one"]:
            issues.append(f"Weather probabilities sum to {prob_sum}, expected 1.0")

        # 3. Combined scenario record count (500 scenarios * 24 hours = 12,000)
        combined_count = len(df_combined)
        checks["combined_records_are_12000"] = (combined_count == 12000)
        if combined_count != 12000:
            issues.append(f"Expected 12,000 combined records, got {combined_count}")

        # 4. Each scenario contains exactly 24 hourly records
        hourly_counts = df_combined.groupby("scenario_id")["hour"].count()
        checks["each_scenario_has_24_hours"] = bool((hourly_counts == 24).all())
        if not checks["each_scenario_has_24_hours"]:
            issues.append("Some scenarios do not have exactly 24 hourly records")

        # 5. Combined scenario probabilities sum to 1.0 across distinct scenarios
        distinct_probs = df_combined.groupby("scenario_id")["probability"].first()
        checks["distinct_scenario_probabilities_sum_to_one"] = bool(np.isclose(distinct_probs.sum(), 1.0, atol=1e-5))

        # 6. No missing values in combined scenarios
        missing_vals = df_combined.isna().sum().sum()
        checks["no_missing_scenario_values"] = (missing_vals == 0)
        if missing_vals > 0:
            issues.append(f"Found {missing_vals} NaN values in combined scenarios")

        # 7. Non-negative demand and solar in scenarios
        checks["scenario_demand_non_negative"] = bool((df_combined["demand_kwh"] >= 0).all())
        checks["scenario_solar_non_negative"] = bool((df_combined["solar_kwh"] >= 0).all())

        stats = {
            "total_scenarios": int(len(distinct_probs)),
            "total_records": combined_count,
            "mean_scenario_demand_kwh": float(df_combined["demand_kwh"].mean()),
            "mean_scenario_solar_kwh": float(df_combined["solar_kwh"].mean()),
            "weather_distribution": df_weather["weather_condition"].value_counts().to_dict(),
        }

        passed = all(checks.values())
        return {
            "dataset": "stochastic_scenarios",
            "passed": passed,
            "checks": checks,
            "statistics": stats,
            "issues": issues,
        }

    def run_full_validation(
        self,
        demand_df: pd.DataFrame,
        solar_df: pd.DataFrame,
        price_df: pd.DataFrame,
        weather_df: pd.DataFrame,
        combined_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Execute full validation suite across all 5 generated datasets."""
        res_demand = self.validate_demand(demand_df)
        res_solar = self.validate_solar(solar_df)
        res_price = self.validate_prices(price_df)
        res_scenarios = self.validate_scenarios(weather_df, combined_df)

        overall_passed = (
            res_demand["passed"]
            and res_solar["passed"]
            and res_price["passed"]
            and res_scenarios["passed"]
        )

        full_report = {
            "timestamp": pd.Timestamp.now().isoformat(),
            "status": "VALIDATED_SUCCESSFULLY" if overall_passed else "VALIDATION_FAILED",
            "overall_passed": overall_passed,
            "datasets": {
                "demand": res_demand,
                "solar": res_solar,
                "prices": res_price,
                "scenarios": res_scenarios,
            },
        }

        # Save JSON validation report
        json_path = self.reports_dir / "validation_report.json"
        clean_report = _sanitize_for_json(full_report)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(clean_report, f, indent=2)

        # Save Text Summary Report
        summary_path = self.reports_dir / "validation_summary.txt"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("====================================================\n")
            f.write("GRIDWISE AI - PHASE 3 DATASET VALIDATION REPORT\n")
            f.write("====================================================\n")
            f.write(f"Generated: {full_report['timestamp']}\n")
            f.write(f"Overall Status: {full_report['status']}\n\n")

            for name, report in full_report["datasets"].items():
                f.write(f"[{name.upper()}] Status: {'PASSED' if report['passed'] else 'FAILED'}\n")
                for check_name, check_val in report["checks"].items():
                    f.write(f"  - {check_name}: {'✔ PASS' if check_val else '❌ FAIL'}\n")
                f.write(f"  Statistics: {report['statistics']}\n")
                if report["issues"]:
                    f.write(f"  Issues: {report['issues']}\n")
                f.write("\n")

        return full_report
