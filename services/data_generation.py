"""
GRIDWISE AI - Master Data Generation Orchestrator
Coordinates synthesis of demand, solar, pricing, weather, and stochastic scenarios.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import pandas as pd

from config.energy_parameters import DEFAULT_ENERGY_PARAMS, EnergyParameters
from config.scenario_parameters import DEFAULT_SCENARIO_PARAMS, ScenarioParameters
from services.demand_generator import CampusDemandGenerator
from services.solar_generator import SolarGenerationGenerator
from services.price_generator import ElectricityPriceGenerator
from services.weather_generator import WeatherScenarioGenerator
from services.scenario_generator import CombinedScenarioGenerator
from services.data_validation import DatasetValidator

logger = logging.getLogger(__name__)


class DataGenerationPipeline:
    """
    Orchestrates the entire Phase 3 synthetic data generation and validation pipeline.
    """

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        energy_params: Optional[EnergyParameters] = None,
        scenario_params: Optional[ScenarioParameters] = None,
    ):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.data_dir = self.base_dir / "data"
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.scenarios_dir = self.data_dir / "scenarios"
        self.reports_dir = self.data_dir / "reports"

        for d in [self.raw_dir, self.processed_dir, self.scenarios_dir, self.reports_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.energy_params = energy_params or DEFAULT_ENERGY_PARAMS
        self.scenario_params = scenario_params or DEFAULT_SCENARIO_PARAMS

    def run_pipeline(self) -> Dict[str, Any]:
        """
        Executes dataset generation, persists CSV files, and runs validation suite.
        """
        logger.info("Starting Phase 3 Dataset Generation Pipeline...")

        # 1. Generate 8760-hour Campus Demand
        print("[1/5] Generating 8760-hour Campus Electricity Demand Dataset...")
        demand_gen = CampusDemandGenerator(seed=self.scenario_params.random_seed)
        df_demand = demand_gen.generate()
        demand_csv = self.processed_dir / "campus_demand_hourly.csv"
        df_demand.to_csv(demand_csv, index=False)
        print(f"      Saved {len(df_demand)} records to {demand_csv.name}")

        # 2. Generate 8760-hour Solar PV Production
        print("[2/5] Generating 8760-hour Solar PV Production Dataset (800 kWp)...")
        solar_gen = SolarGenerationGenerator(
            solar_capacity_kwp=self.energy_params.solar_installed_capacity_kwp,
            seed=self.scenario_params.random_seed,
        )
        df_solar = solar_gen.generate()
        solar_csv = self.processed_dir / "solar_generation_hourly.csv"
        df_solar.to_csv(solar_csv, index=False)
        print(f"      Saved {len(df_solar)} records to {solar_csv.name}")

        # 3. Generate 8760-hour TOU Electricity Prices
        print("[3/5] Generating 8760-hour Simulated TOU Electricity Price Dataset...")
        price_gen = ElectricityPriceGenerator(seed=self.scenario_params.random_seed)
        df_price = price_gen.generate()
        price_csv = self.processed_dir / "electricity_prices_hourly.csv"
        df_price.to_csv(price_csv, index=False)
        print(f"      Saved {len(df_price)} records to {price_csv.name}")

        # 4. Generate 500 Weather Scenarios
        print("[4/5] Generating 500 Reproducible Weather Scenarios...")
        weather_gen = WeatherScenarioGenerator(self.scenario_params)
        df_weather = weather_gen.generate()
        weather_csv = self.scenarios_dir / "weather_scenarios_500.csv"
        df_weather.to_csv(weather_csv, index=False)
        print(f"      Saved {len(df_weather)} scenarios to {weather_csv.name}")

        # 5. Generate 500 Combined Stochastic Scenarios (12,000 records)
        print("[5/5] Generating 500 Combined 24-Hour Stochastic Scenarios (12,000 records)...")
        scen_gen = CombinedScenarioGenerator(self.scenario_params, self.energy_params)
        df_demand_scen = scen_gen.generate_demand_scenarios()
        demand_scen_csv = self.scenarios_dir / "demand_scenarios_500.csv"
        df_demand_scen.to_csv(demand_scen_csv, index=False)

        df_combined = scen_gen.generate_combined_scenarios()
        combined_csv = self.scenarios_dir / "combined_scenarios_500.csv"
        df_combined.to_csv(combined_csv, index=False)
        print(f"      Saved {len(df_combined)} combined records to {combined_csv.name}")

        # 6. Run Validation Engine
        print("\n[VALIDATION] Executing Comprehensive Data Validation Suite...")
        validator = DatasetValidator(str(self.data_dir))
        validation_report = validator.run_full_validation(
            demand_df=df_demand,
            solar_df=df_solar,
            price_df=df_price,
            weather_df=df_weather,
            combined_df=df_combined,
        )

        print(f"             Validation Result: {validation_report['status']}")
        return {
            "validation_report": validation_report,
            "record_counts": {
                "demand_8760": len(df_demand),
                "solar_8760": len(df_solar),
                "prices_8760": len(df_price),
                "weather_scenarios": len(df_weather),
                "combined_records": len(df_combined),
            },
        }


def run_full_data_generation() -> Dict[str, Any]:
    """CLI / Service entry point to run full dataset generation."""
    pipeline = DataGenerationPipeline()
    return pipeline.run_pipeline()
