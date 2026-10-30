"""
GRIDWISE AI - Scenario Loader and Validator
Loads and rigorously validates Phase 3 stochastic microgrid scenarios for optimization.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
SCENARIOS_DIR = BASE_DIR / "data" / "scenarios"


class ScenarioValidationError(Exception):
    """Raised when scenario dataset fails strict validation rules."""
    pass


class ScenarioLoader:
    """Loads and validates stochastic microgrid scenarios."""

    DEFAULT_FILES = [
        SCENARIOS_DIR / "combined_scenarios.csv",
        SCENARIOS_DIR / "combined_scenarios_500.csv",
    ]

    @classmethod
    def find_scenario_file(cls, filepath: Optional[Path] = None) -> Path:
        """Locates the primary combined scenario CSV file."""
        if filepath is not None:
            p = Path(filepath)
            if p.exists():
                return p
            raise FileNotFoundError(f"Specified scenario file not found: {filepath}")

        for candidate in cls.DEFAULT_FILES:
            if candidate.exists():
                return candidate

        raise FileNotFoundError(
            f"No scenario dataset found in {SCENARIOS_DIR}. "
            "Please run 'python scripts/generate_dataset.py' to generate Phase 3 datasets."
        )

    @classmethod
    def load_and_validate(
        cls,
        filepath: Optional[Path] = None,
        max_scenarios: Optional[int] = None,
        normalize_subset_probabilities: bool = True,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Loads and performs strict validation on combined scenario dataset.

        Parameters
        ----------
        filepath : Optional[Path]
            Custom path to scenario CSV.
        max_scenarios : Optional[int]
            If specified, extracts the first N scenarios (useful for fast testing).
        normalize_subset_probabilities : bool
            If max_scenarios is set, re-normalizes scenario probabilities to sum to 1.0.

        Returns
        -------
        Tuple[pd.DataFrame, Dict[str, Any]]
            Validated DataFrame and a validation metadata dictionary.

        Raises
        ------
        ScenarioValidationError
            If any mathematical or physical integrity check fails.
        """
        target_path = cls.find_scenario_file(filepath)
        logger.info(f"Loading scenario data from: {target_path}")

        try:
            df = pd.read_csv(target_path)
        except Exception as e:
            raise ScenarioValidationError(f"Failed to read CSV at {target_path}: {e}") from e

        # 1. Verify required columns
        required_cols = {"scenario_id", "hour", "probability", "demand_kwh"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise ScenarioValidationError(
                f"Missing mandatory columns in scenario file: {missing_cols}. Found: {df.columns.tolist()}"
            )

        # Standardize solar column name if needed
        if "solar_kwh" not in df.columns and "solar_generation_kwh" in df.columns:
            df["solar_kwh"] = df["solar_generation_kwh"]
        elif "solar_kwh" not in df.columns:
            raise ScenarioValidationError("Scenario file must contain 'solar_kwh' or 'solar_generation_kwh'.")

        # 2. Check empty or nulls
        if df.empty:
            raise ScenarioValidationError(f"Scenario dataset at {target_path} is completely empty.")

        null_counts = df[["scenario_id", "hour", "probability", "demand_kwh", "solar_kwh"]].isnull().sum()
        if null_counts.any():
            raise ScenarioValidationError(
                f"Scenario dataset contains null / NaN values: {null_counts[null_counts > 0].to_dict()}"
            )

        # 3. Verify hourly observations per scenario
        scenario_groups = df.groupby("scenario_id")
        unique_scenarios = list(scenario_groups.groups.keys())
        total_unique = len(unique_scenarios)

        if total_unique == 0:
            raise ScenarioValidationError("No distinct scenario IDs found in dataset.")

        hours_per_scenario = scenario_groups["hour"].count().unique()
        if len(hours_per_scenario) != 1 or hours_per_scenario[0] != 24:
            invalid_scenarios = scenario_groups["hour"].count()
            bad = invalid_scenarios[invalid_scenarios != 24]
            raise ScenarioValidationError(
                f"All scenarios must contain exactly 24 hourly observations. "
                f"Found non-24 hour scenarios: {bad.head().to_dict()} (counts: {hours_per_scenario})"
            )

        # 4. Check hours span 0 to 23
        for scen_id, group in scenario_groups:
            hours_set = set(group["hour"].tolist())
            if hours_set != set(range(24)):
                raise ScenarioValidationError(
                    f"Scenario {scen_id} does not span hours 0 through 23. Found hours: {sorted(hours_set)}"
                )
            break  # Sampling first is sufficient given the 24 count check

        # 5. Check probabilities
        first_prob_per_scen = scenario_groups["probability"].first()
        if (first_prob_per_scen <= 0).any():
            raise ScenarioValidationError("Scenario probabilities must be strictly positive (> 0).")
        if (first_prob_per_scen > 1.0).any():
            raise ScenarioValidationError("Scenario probabilities cannot exceed 1.0.")

        total_prob = float(first_prob_per_scen.sum())
        if not np.isclose(total_prob, 1.0, atol=1e-4):
            raise ScenarioValidationError(
                f"Scenario probabilities must sum to 1.0 (within 1e-4). Found sum: {total_prob:.6f}"
            )

        # 6. Physical non-negativity checks
        if (df["demand_kwh"] < 0).any():
            min_dem = df["demand_kwh"].min()
            raise ScenarioValidationError(f"Campus electricity demand cannot be negative. Found min: {min_dem}")

        if (df["solar_kwh"] < 0).any():
            min_sol = df["solar_kwh"].min()
            raise ScenarioValidationError(f"Solar PV generation cannot be negative. Found min: {min_sol}")

        # Subset scenarios if requested
        if max_scenarios is not None and max_scenarios < total_unique:
            selected_ids = unique_scenarios[:max_scenarios]
            df = df[df["scenario_id"].isin(selected_ids)].copy()
            if normalize_subset_probabilities:
                sub_probs = df.groupby("scenario_id")["probability"].first()
                norm_factor = float(sub_probs.sum())
                prob_map = (sub_probs / norm_factor).to_dict()
                df["probability"] = df["scenario_id"].map(prob_map)
            logger.info(f"Subsetting to first {max_scenarios} scenarios. Normalized probability sum: {df.groupby('scenario_id')['probability'].first().sum():.6f}")

        # Metadata summary
        meta = {
            "source_file": str(target_path),
            "total_records": len(df),
            "total_scenarios": len(df["scenario_id"].unique()),
            "probability_sum": float(df.groupby("scenario_id")["probability"].first().sum()),
            "min_demand_kwh": float(df["demand_kwh"].min()),
            "max_demand_kwh": float(df["demand_kwh"].max()),
            "min_solar_kwh": float(df["solar_kwh"].min()),
            "max_solar_kwh": float(df["solar_kwh"].max()),
            "validation_status": "PASSED",
        }

        logger.info(f"Scenario validation SUCCESSFUL: {meta['total_scenarios']} scenarios validated.")
        return df, meta

    @classmethod
    def get_expected_profiles(cls, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Computes probability-weighted expected 24-hour profiles for demand, solar, and prices.

        Returns
        -------
        Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]
            (expected_demand_24h, expected_solar_24h, da_prices_24h, rt_prices_24h)
        """
        scenarios = df["scenario_id"].unique()
        probs = df.groupby("scenario_id")["probability"].first().values
        
        # Reshape to (N, 24)
        demand_matrix = df.pivot(index="scenario_id", columns="hour", values="demand_kwh").loc[scenarios].values
        solar_matrix = df.pivot(index="scenario_id", columns="hour", values="solar_kwh").loc[scenarios].values
        
        # Weighted expectation across scenarios
        exp_demand = np.sum(demand_matrix * probs[:, np.newaxis], axis=0)
        exp_solar = np.sum(solar_matrix * probs[:, np.newaxis], axis=0)

        # Prices (Day-Ahead is deterministic/scenario-independent, RT is scenario-dependent)
        if "day_ahead_price_inr_kwh" in df.columns:
            da_prices = df.groupby("hour")["day_ahead_price_inr_kwh"].first().sort_index().values
        else:
            # Standard TOU fallback schedule
            da_prices = np.array([4.2]*6 + [7.5]*8 + [11.8]*6 + [7.5]*2 + [4.2]*2)

        if "real_time_price_inr_kwh" in df.columns:
            rt_matrix = df.pivot(index="scenario_id", columns="hour", values="real_time_price_inr_kwh").loc[scenarios].values
            rt_prices = np.sum(rt_matrix * probs[:, np.newaxis], axis=0)
        else:
            rt_prices = da_prices * 1.05

        return exp_demand, exp_solar, da_prices, rt_prices

