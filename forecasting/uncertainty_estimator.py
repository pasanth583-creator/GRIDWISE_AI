"""
GRIDWISE AI - Forecast Uncertainty Estimator & Scenario Generator
Combines demand, solar, and price point forecasts with empirical residual distributions
to construct 24-hour joint probabilistic forecast scenarios for stochastic optimization.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import numpy as np
import pandas as pd

from forecasting.demand_forecaster import CampusDemandForecaster
from forecasting.solar_forecaster import SolarGenerationForecaster
from forecasting.price_forecaster import ElectricityPriceForecaster

BASE_DIR = Path(__file__).resolve().parent.parent
FORECASTS_DIR = BASE_DIR / "data" / "forecasts"
FORECASTS_DIR.mkdir(parents=True, exist_ok=True)


class ForecastUncertaintyEstimator:
    """
    Coordinates multi-target forecasting (demand, solar, prices), estimates joint uncertainty,
    and constructs normalized 24-hour forecast scenarios for the stochastic optimizer.
    """

    def __init__(self, random_seed: int = 42):
        self.random_seed = random_seed
        self.demand_forecaster = CampusDemandForecaster(random_state=random_seed)
        self.solar_forecaster = SolarGenerationForecaster(random_state=random_seed)
        self.da_price_forecaster = ElectricityPriceForecaster(random_state=random_seed)
        self.rt_price_forecaster = ElectricityPriceForecaster(random_state=random_seed)

        self.evaluation_summary: Dict[str, Any] = {}
        self.comparison_records: List[Dict[str, Any]] = []

    def fit_all_models(
        self,
        demand_df: pd.DataFrame,
        solar_df: pd.DataFrame,
        price_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Trains and validates demand, solar, and price forecasters."""
        # 1. Demand
        dem_eval = self.demand_forecaster.train_and_evaluate(demand_df)
        self.evaluation_summary["demand"] = dem_eval
        for m_name, metrics in dem_eval["validation_comparison"].items():
            self.comparison_records.append({
                "target": "demand",
                "model": m_name,
                "is_selected": (m_name == dem_eval["selected_model"]),
                **metrics,
            })

        # 2. Solar
        sol_eval = self.solar_forecaster.train_and_evaluate(solar_df)
        self.evaluation_summary["solar"] = sol_eval
        for m_name, metrics in sol_eval["validation_comparison"].items():
            self.comparison_records.append({
                "target": "solar",
                "model": m_name,
                "is_selected": (m_name == sol_eval["selected_model"]),
                **metrics,
            })

        # 3. Prices
        da_eval = self.da_price_forecaster.train_and_evaluate(price_df, target_col="day_ahead_price_inr_kwh")
        rt_eval = self.rt_price_forecaster.train_and_evaluate(price_df, target_col="real_time_price_inr_kwh")
        self.evaluation_summary["day_ahead_price"] = da_eval
        self.evaluation_summary["real_time_price"] = rt_eval
        for m_name, metrics in rt_eval["validation_comparison"].items():
            self.comparison_records.append({
                "target": "real_time_price",
                "model": m_name,
                "is_selected": (m_name == rt_eval["selected_model"]),
                **metrics,
            })

        return self.evaluation_summary

    def generate_forecasts_and_scenarios(
        self,
        demand_df: pd.DataFrame,
        solar_df: pd.DataFrame,
        price_df: pd.DataFrame,
        num_scenarios: int = 50,
    ) -> Dict[str, Any]:
        """
        Generates 24-hour ahead predictions, uncertainty intervals, and empirical scenarios.
        Saves all outputs into data/forecasts/.
        """
        np.random.seed(self.random_seed)

        # Generate 24h point forecasts
        df_dem_fc = self.demand_forecaster.predict_next_24h(demand_df)
        df_sol_fc = self.solar_forecaster.predict_next_24h(solar_df)
        df_da_fc = self.da_price_forecaster.predict_next_24h(price_df, target_col="day_ahead_price_inr_kwh")
        df_rt_fc = self.rt_price_forecaster.predict_next_24h(price_df, target_col="real_time_price_inr_kwh")

        # 1. Save individual forecast CSV files
        dem_file = FORECASTS_DIR / "demand_forecast.csv"
        sol_file = FORECASTS_DIR / "solar_forecast.csv"
        price_file = FORECASTS_DIR / "price_forecast.csv"

        df_dem_fc.to_csv(dem_file, index=False)
        df_sol_fc.to_csv(sol_file, index=False)

        df_prices_fc = pd.DataFrame({
            "hour": df_da_fc["hour"],
            "predicted_day_ahead_price_inr_kwh": df_da_fc["predicted_day_ahead_price_inr_kwh"],
            "predicted_real_time_price_inr_kwh": df_rt_fc["predicted_real_time_price_inr_kwh"],
            "price_ci_lower_inr_kwh": df_rt_fc["price_ci_lower_inr_kwh"],
            "price_ci_upper_inr_kwh": df_rt_fc["price_ci_upper_inr_kwh"],
        })
        df_prices_fc.to_csv(price_file, index=False)

        # 2. Combined intervals CSV
        df_intervals = pd.DataFrame({
            "hour": df_dem_fc["hour"],
            "demand_forecast_kwh": df_dem_fc["predicted_demand_kwh"],
            "demand_lower_kwh": df_dem_fc["demand_ci_lower_kwh"],
            "demand_upper_kwh": df_dem_fc["demand_ci_upper_kwh"],
            "solar_forecast_kwh": df_sol_fc["predicted_solar_kwh"],
            "solar_lower_kwh": df_sol_fc["solar_ci_lower_kwh"],
            "solar_upper_kwh": df_sol_fc["solar_ci_upper_kwh"],
            "da_price_inr_kwh": df_prices_fc["predicted_day_ahead_price_inr_kwh"],
            "rt_price_forecast_inr_kwh": df_prices_fc["predicted_real_time_price_inr_kwh"],
            "rt_price_lower_inr_kwh": df_prices_fc["price_ci_lower_inr_kwh"],
            "rt_price_upper_inr_kwh": df_prices_fc["price_ci_upper_inr_kwh"],
        })
        intervals_file = FORECASTS_DIR / "forecast_intervals.csv"
        df_intervals.to_csv(intervals_file, index=False)

        # 3. Construct Forecast Scenarios for Stochastic Optimization
        # Sample correlated residual shifts around point forecasts across weather regimes
        scenario_rows = []
        p_scenario = 1.0 / float(num_scenarios)
        weather_regimes = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy"]
        regime_solar_multipliers = {"Sunny": 1.15, "Partly Cloudy": 0.95, "Cloudy": 0.65, "Rainy": 0.30}
        regime_demand_multipliers = {"Sunny": 0.98, "Partly Cloudy": 1.00, "Cloudy": 1.04, "Rainy": 1.08}
        regime_probs = [0.35, 0.30, 0.20, 0.15]

        for s_idx in range(num_scenarios):
            sid = f"FC_SCEN_{s_idx+1:04d}"
            regime = np.random.choice(weather_regimes, p=regime_probs)
            sol_mult = regime_solar_multipliers[regime]
            dem_mult = regime_demand_multipliers[regime]

            # Correlated random shock
            z_common = np.random.normal(0.0, 0.05)

            for t in range(24):
                base_d = df_dem_fc["predicted_demand_kwh"].iloc[t]
                base_s = df_sol_fc["predicted_solar_kwh"].iloc[t]
                da_p = df_prices_fc["predicted_day_ahead_price_inr_kwh"].iloc[t]
                rt_p = df_prices_fc["predicted_real_time_price_inr_kwh"].iloc[t]

                # Sample demand with regime effect + random noise
                d_shock = np.random.normal(0.0, 0.04)
                d_val = float(np.maximum(100.0, base_d * dem_mult * (1.0 + z_common + d_shock)))

                # Sample solar (strictly 0 at night)
                if t in SolarGenerationForecaster.NIGHT_HOURS:
                    s_val = 0.0
                else:
                    s_shock = np.random.normal(0.0, 0.08)
                    s_val = float(np.clip(base_s * sol_mult * (1.0 - z_common + s_shock), 0.0, 800.0))

                # Real-time price shock
                p_shock = np.random.normal(0.0, 0.06)
                rt_val = float(np.maximum(1.0, rt_p * (1.0 + p_shock)))

                scenario_rows.append({
                    "scenario_id": sid,
                    "hour": t,
                    "weather_condition": regime,
                    "probability": round(p_scenario, 8),
                    "demand_kwh": round(d_val, 2),
                    "solar_kwh": round(s_val, 2),
                    "day_ahead_price_inr_kwh": round(float(da_p), 3),
                    "real_time_price_inr_kwh": round(rt_val, 3),
                })

        df_scenarios = pd.DataFrame(scenario_rows)
        # Normalize probabilities strictly
        unique_scens = df_scenarios["scenario_id"].unique()
        norm_prob = 1.0 / len(unique_scens)
        df_scenarios["probability"] = norm_prob

        scen_file = FORECASTS_DIR / "forecast_scenarios.csv"
        df_scenarios.to_csv(scen_file, index=False)

        # 4. Save model evaluation and comparison
        eval_file = FORECASTS_DIR / "model_evaluation.json"
        with open(eval_file, "w") as f:
            json.dump(self.evaluation_summary, f, indent=2)

        comp_file = FORECASTS_DIR / "model_comparison.csv"
        df_comp = pd.DataFrame(self.comparison_records)
        df_comp.to_csv(comp_file, index=False)

        return {
            "status": "SUCCESS",
            "saved_files": {
                "demand_forecast": str(dem_file),
                "solar_forecast": str(sol_file),
                "price_forecast": str(price_file),
                "forecast_intervals": str(intervals_file),
                "forecast_scenarios": str(scen_file),
                "model_evaluation": str(eval_file),
                "model_comparison": str(comp_file),
            },
            "num_scenarios_generated": num_scenarios,
            "probability_sum": float(df_scenarios.groupby("scenario_id")["probability"].first().sum()),
        }

    def generate_all_forecasts(self, num_scenarios: int = 50) -> Dict[str, Any]:
        """Loads historical data from data/processed/, fits models, and generates all forecasts and scenarios."""
        proc_dir = BASE_DIR / "data" / "processed"
        dem_path = proc_dir / "campus_demand_hourly.csv"
        sol_path = proc_dir / "solar_generation_hourly.csv"
        pri_path = proc_dir / "electricity_prices_hourly.csv"

        df_dem = pd.read_csv(dem_path)
        df_sol = pd.read_csv(sol_path)
        df_pri = pd.read_csv(pri_path)

        eval_summary = self.fit_all_models(df_dem, df_sol, df_pri)
        gen_result = self.generate_forecasts_and_scenarios(df_dem, df_sol, df_pri, num_scenarios=num_scenarios)
        gen_result["evaluation"] = eval_summary
        return gen_result

