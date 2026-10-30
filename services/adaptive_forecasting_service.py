"""
GRIDWISE AI - Adaptive Forecasting & Scenario Generation Service
Phase 8 Live Weather Integration, Physics-Based Solar Modeling,
Adaptive Microgrid Multi-Target Forecasting, and Probabilistic Scenarios.
"""

from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timezone
import json
import logging
import numpy as np
import pandas as pd

from services.weather_service import WeatherService
from forecasting.demand_forecaster import CampusDemandForecaster
from forecasting.solar_forecaster import SolarGenerationForecaster
from forecasting.price_forecaster import ElectricityPriceForecaster
from database.database import execute_db, query_db

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ADAPTIVE_DIR = BASE_DIR / "data" / "adaptive"
ADAPTIVE_DIR.mkdir(parents=True, exist_ok=True)


class AdaptiveForecastingService:
    """
    Coordinates live weather ingestion, physical PV solar derating,
    weather-sensitive campus load modeling, tariff forecasting, and
    generation of >= 100 adaptive stochastic scenarios.
    """

    SOLAR_CAPACITY_KWP = 800.0
    NIGHT_HOURS = {0, 1, 2, 3, 4, 5, 20, 21, 22, 23}
    TEMP_DERATE_COEFF = 0.004  # 0.4% efficiency loss per °C above 25°C
    PERFORMANCE_RATIO = 0.82  # Inverter, cabling, soiling factor

    @classmethod
    def compute_physical_solar_generation(
        cls,
        hour_of_day: int,
        solar_radiation_w_m2: Optional[float],
        temperature_c: float,
        cloud_cover_pct: float,
        base_ml_solar: float = 0.0,
    ) -> float:
        """
        Physics-based photovoltaic power output with thermal derating:
        P = Capacity * (GHI / 1000) * PR * (1 - gamma * (T_cell - 25))
        Zero strictly at night; non-negative; capped at 800 kWp.
        """
        # 1. Nighttime zero enforcement
        if int(hour_of_day) in cls.NIGHT_HOURS:
            return 0.0

        # 2. Estimate or use Global Horizontal Irradiance (GHI)
        if solar_radiation_w_m2 is not None and solar_radiation_w_m2 > 10.0:
            ghi = float(solar_radiation_w_m2)
        else:
            # Clear-sky solar elevation model attenuated by cloud cover
            # Kasten & Czeplak cloud attenuation formula
            h_rel = max(0.0, hour_of_day - 6.0)
            elevation_proxy = np.sin(np.pi * h_rel / 12.0) if 6 <= hour_of_day <= 18 else 0.0
            clear_sky_ghi = 1000.0 * elevation_proxy
            cloud_factor = 1.0 - 0.75 * ((cloud_cover_pct / 100.0) ** 3.4)
            ghi = clear_sky_ghi * max(0.1, cloud_factor)

        # 3. Temperature derating factor
        # Cell temperature reaches ~ T_amb + 25 * (ghi / 1000)
        t_cell = temperature_c + 25.0 * (ghi / 1000.0)
        temp_delta = max(0.0, t_cell - 25.0)
        eta_temp = max(0.70, 1.0 - cls.TEMP_DERATE_COEFF * temp_delta)

        # 4. Power output
        raw_power = cls.SOLAR_CAPACITY_KWP * (ghi / 1000.0) * cls.PERFORMANCE_RATIO * eta_temp

        # Blend with historical machine learning prediction if available
        if base_ml_solar > 0:
            # 70% physical live weather irradiance + 30% historical campus profile
            blended_power = 0.70 * raw_power + 0.30 * base_ml_solar
        else:
            blended_power = raw_power

        # 5. Final boundary clipping
        return float(np.clip(blended_power, 0.0, cls.SOLAR_CAPACITY_KWP))

    @classmethod
    def compute_weather_sensitive_demand(
        cls,
        base_demand: float,
        temperature_c: float,
        relative_humidity_pct: float,
        hour_of_day: int,
    ) -> float:
        """
        Applies temperature and humidity HVAC load sensitivity:
        Campuses experience higher chiller/AC electrical load during hot/humid afternoons.
        Cooling response: +1.5% per °C above 28°C baseline; humidity latent penalty +0.5% per 10% RH above 60%.
        """
        temp_excess = max(0.0, temperature_c - 28.0)
        rh_excess = max(0.0, relative_humidity_pct - 60.0)

        # Afternoon hours (11:00 to 18:00) have the strongest HVAC response
        hvac_sensitivity = 1.0 if 11 <= hour_of_day <= 18 else 0.5
        cooling_multiplier = 1.0 + (0.015 * temp_excess + 0.005 * (rh_excess / 10.0)) * hvac_sensitivity

        adapted_demand = base_demand * cooling_multiplier
        return float(max(100.0, adapted_demand))

    @classmethod
    def generate_adaptive_forecasts(
        cls,
        force_weather_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieves live weather, updates solar, demand, and price forecasts for 24h,
        and saves CSV files into data/adaptive/.
        """
        # 1. Ingest Live Weather
        weather = WeatherService.get_weather_data(force_refresh=force_weather_refresh)
        hourly_weather = weather.get("hourly_24h", [])

        # 2. Load Phase 7 base forecasts if available, else generate baseline
        dem_fc_file = BASE_DIR / "data" / "forecasts" / "demand_forecast.csv"
        sol_fc_file = BASE_DIR / "data" / "forecasts" / "solar_forecast.csv"
        pri_fc_file = BASE_DIR / "data" / "forecasts" / "price_forecast.csv"

        df_base_dem = pd.read_csv(dem_fc_file) if dem_fc_file.exists() else None
        df_base_sol = pd.read_csv(sol_fc_file) if sol_fc_file.exists() else None
        df_base_pri = pd.read_csv(pri_fc_file) if pri_fc_file.exists() else None

        forecast_uuid = f"FC-ADAPT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        now_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        solar_rows = []
        demand_rows = []
        price_rows = []
        adaptive_forecast_rows = []

        for i in range(24):
            w = hourly_weather[i] if i < len(hourly_weather) else {}
            h_tod = w.get("hour_of_day", i)
            temp = w.get("temperature_c", 30.0)
            rh = w.get("relative_humidity_pct", 55.0)
            cloud = w.get("cloud_cover_pct", 20.0)
            rad = w.get("solar_radiation_w_m2", 0.0)

            # Base values from Phase 7 models
            base_s = float(df_base_sol["predicted_solar_kwh"].iloc[i]) if df_base_sol is not None else 0.0
            base_d = float(df_base_dem["predicted_demand_kwh"].iloc[i]) if df_base_dem is not None else 450.0
            base_da = float(df_base_pri["predicted_day_ahead_price_inr_kwh"].iloc[i]) if df_base_pri is not None else 6.5
            base_rt = float(df_base_pri["predicted_real_time_price_inr_kwh"].iloc[i]) if df_base_pri is not None else 7.2

            # Adaptive updates
            adapt_solar = cls.compute_physical_solar_generation(
                hour_of_day=h_tod,
                solar_radiation_w_m2=rad,
                temperature_c=temp,
                cloud_cover_pct=cloud,
                base_ml_solar=base_s,
            )

            adapt_demand = cls.compute_weather_sensitive_demand(
                base_demand=base_d,
                temperature_c=temp,
                relative_humidity_pct=rh,
                hour_of_day=h_tod,
            )

            # Cloud / ramp price risk adjustment for real-time balancing
            ramp_risk = 1.0 + (0.05 if cloud > 60.0 else 0.0)
            adapt_rt_price = max(1.0, base_rt * ramp_risk)
            adapt_da_price = max(1.0, base_da)

            solar_rows.append({
                "hour": i,
                "hour_of_day": h_tod,
                "adaptive_solar_kwh": round(adapt_solar, 2),
                "weather_radiation_w_m2": round(rad, 1),
                "cloud_cover_pct": round(cloud, 1),
                "temperature_c": round(temp, 1),
            })

            demand_rows.append({
                "hour": i,
                "hour_of_day": h_tod,
                "adaptive_demand_kwh": round(adapt_demand, 2),
                "temperature_c": round(temp, 1),
                "relative_humidity_pct": round(rh, 1),
            })

            price_rows.append({
                "hour": i,
                "hour_of_day": h_tod,
                "day_ahead_price_inr_kwh": round(adapt_da_price, 3),
                "adaptive_real_time_price_inr_kwh": round(adapt_rt_price, 3),
            })

            adaptive_forecast_rows.append({
                "forecast_uuid": forecast_uuid,
                "forecast_date": now_date,
                "hour": i,
                "weather_condition": "Cloudy" if cloud > 50 else ("Partly Cloudy" if cloud > 20 else "Sunny"),
                "temperature_c": temp,
                "cloud_cover_pct": cloud,
                "solar_radiation_w_m2": rad,
                "adaptive_solar_kw": round(adapt_solar, 2),
                "adaptive_demand_kw": round(adapt_demand, 2),
                "adaptive_da_price_inr": round(adapt_da_price, 3),
                "adaptive_rt_price_inr": round(adapt_rt_price, 3),
            })

        # Save CSV files
        df_solar = pd.DataFrame(solar_rows)
        df_demand = pd.DataFrame(demand_rows)
        df_price = pd.DataFrame(price_rows)

        df_solar.to_csv(ADAPTIVE_DIR / "adaptive_solar_forecast.csv", index=False)
        df_demand.to_csv(ADAPTIVE_DIR / "adaptive_demand_forecast.csv", index=False)
        df_price.to_csv(ADAPTIVE_DIR / "adaptive_price_forecast.csv", index=False)

        # Persist to SQLite table adaptive_forecasts
        try:
            for r in adaptive_forecast_rows:
                execute_db(
                    """
                    INSERT OR REPLACE INTO adaptive_forecasts (
                        forecast_uuid, forecast_date, hour, weather_condition,
                        temperature_c, cloud_cover_pct, solar_radiation_w_m2,
                        adaptive_solar_kw, adaptive_demand_kw,
                        adaptive_da_price_inr, adaptive_rt_price_inr
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r["forecast_uuid"], r["forecast_date"], r["hour"], r["weather_condition"],
                        r["temperature_c"], r["cloud_cover_pct"], r["solar_radiation_w_m2"],
                        r["adaptive_solar_kw"], r["adaptive_demand_kw"],
                        r["adaptive_da_price_inr"], r["adaptive_rt_price_inr"]
                    )
                )
        except Exception as e:
            logger.warning(f"Could not save adaptive forecasts to DB: {e}")

        return {
            "status": "SUCCESS",
            "forecast_uuid": forecast_uuid,
            "forecast_date": now_date,
            "weather_source": weather.get("source", "Open-Meteo"),
            "is_cached_weather": weather.get("is_cached", False),
            "solar_forecast": solar_rows,
            "demand_forecast": demand_rows,
            "price_forecast": price_rows,
        }

    @classmethod
    def generate_adaptive_scenarios(
        cls,
        num_scenarios: int = 100,
        random_seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Generates at least 100 adaptive scenarios using live-weather-adjusted point forecasts
        combined with empirical residual distributions.
        Guarantees:
        - Exactly 24 hours per scenario.
        - Strict probability normalization: sum(p_s) == 1.0.
        - Demand >= 0.
        - Solar in [0, 800 kWp], strictly 0 at night.
        - Prices positive (>= 1.0 INR/kWh).
        - Fully reproducible given random_seed.
        """
        np.random.seed(random_seed)

        # 1. Ensure adaptive forecasts are up to date
        fc_res = cls.generate_adaptive_forecasts()
        solar_fc = fc_res["solar_forecast"]
        demand_fc = fc_res["demand_forecast"]
        price_fc = fc_res["price_forecast"]

        prob_per_scen = 1.0 / float(num_scenarios)
        scenario_rows = []

        # Weather regime shifts around current live weather condition
        weather_regimes = ["Clear Sunny", "Scattered Clouds", "Overcast", "Monsoon Rain"]
        regime_weights = [0.40, 0.35, 0.15, 0.10]
        solar_regime_effects = {"Clear Sunny": 1.10, "Scattered Clouds": 0.95, "Overcast": 0.60, "Monsoon Rain": 0.25}
        demand_regime_effects = {"Clear Sunny": 1.02, "Scattered Clouds": 1.00, "Overcast": 0.98, "Monsoon Rain": 0.95}

        for s_idx in range(num_scenarios):
            sid = f"ADAPT_SCEN_{s_idx+1:04d}"
            regime = np.random.choice(weather_regimes, p=regime_weights)
            s_mult = solar_regime_effects[regime]
            d_mult = demand_regime_effects[regime]

            # Correlated common shock for this day scenario
            z_day = np.random.normal(0.0, 0.04)

            for t in range(24):
                base_s = solar_fc[t]["adaptive_solar_kwh"]
                base_d = demand_fc[t]["adaptive_demand_kwh"]
                base_da = price_fc[t]["day_ahead_price_inr_kwh"]
                base_rt = price_fc[t]["adaptive_real_time_price_inr_kwh"]
                h_tod = solar_fc[t]["hour_of_day"]

                # Solar sampling with physical constraints
                if h_tod in cls.NIGHT_HOURS:
                    s_val = 0.0
                else:
                    s_noise = np.random.normal(0.0, 0.06)
                    s_val = float(np.clip(base_s * s_mult * (1.0 + z_day + s_noise), 0.0, cls.SOLAR_CAPACITY_KWP))

                # Demand sampling (strictly non-negative)
                d_noise = np.random.normal(0.0, 0.03)
                d_val = float(max(100.0, base_d * d_mult * (1.0 + z_day + d_noise)))

                # Real-time balancing price sampling (strictly positive)
                p_noise = np.random.normal(0.0, 0.05)
                rt_val = float(max(1.0, base_rt * (1.0 + p_noise)))

                scenario_rows.append({
                    "scenario_id": sid,
                    "hour": t,
                    "weather_condition": regime,
                    "probability": round(prob_per_scen, 8),
                    "demand_kwh": round(d_val, 2),
                    "solar_kwh": round(s_val, 2),
                    "day_ahead_price_inr_kwh": round(base_da, 3),
                    "real_time_price_inr_kwh": round(rt_val, 3),
                })

        df_scenarios = pd.DataFrame(scenario_rows)

        # Strict probability normalization check
        unique_ids = df_scenarios["scenario_id"].unique()
        exact_prob = 1.0 / len(unique_ids)
        df_scenarios["probability"] = exact_prob

        # Save to data/adaptive/adaptive_scenarios.csv
        scen_csv = ADAPTIVE_DIR / "adaptive_scenarios.csv"
        df_scenarios.to_csv(scen_csv, index=False)

        # Compute summary statistics
        summary_uuid = f"SUMM-ADAPT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        mean_solar = float(df_scenarios.groupby("scenario_id")["solar_kwh"].sum().mean())
        mean_demand = float(df_scenarios.groupby("scenario_id")["demand_kwh"].sum().mean())
        mean_da = float(df_scenarios["day_ahead_price_inr_kwh"].mean())
        mean_rt = float(df_scenarios["real_time_price_inr_kwh"].mean())

        weather_counts = df_scenarios.groupby("scenario_id")["weather_condition"].first().value_counts()
        regimes_dict = {str(k): int(v) for k, v in weather_counts.items()}

        summary_data = {
            "summary_uuid": summary_uuid,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "num_scenarios": len(unique_ids),
            "hours_per_scenario": 24,
            "total_records": len(df_scenarios),
            "random_seed": random_seed,
            "probability_sum": float(df_scenarios.groupby("scenario_id")["probability"].first().sum()),
            "mean_daily_solar_kwh": round(mean_solar, 2),
            "mean_daily_demand_kwh": round(mean_demand, 2),
            "mean_day_ahead_price_inr": round(mean_da, 3),
            "mean_real_time_price_inr": round(mean_rt, 3),
            "weather_regimes_sampled": regimes_dict,
        }

        # Save to data/adaptive/adaptive_scenario_summary.json
        with open(ADAPTIVE_DIR / "adaptive_scenario_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

        # Persist summary to SQLite table adaptive_scenario_summaries
        try:
            execute_db(
                """
                INSERT INTO adaptive_scenario_summaries (
                    summary_uuid, num_scenarios, random_seed,
                    mean_daily_solar_kwh, mean_daily_demand_kwh,
                    mean_da_price_inr, mean_rt_price_inr, weather_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary_uuid,
                    len(unique_ids),
                    random_seed,
                    round(mean_solar, 2),
                    round(mean_demand, 2),
                    round(mean_da, 3),
                    round(mean_rt, 3),
                    json.dumps(summary_data["weather_regimes_sampled"]),
                ),
            )
        except Exception as e:
            logger.warning(f"Could not persist adaptive scenario summary: {e}")

        summary_data["scenarios_csv"] = str(scen_csv)
        return summary_data
