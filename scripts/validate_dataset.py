"""
GRIDWISE AI - Dataset Validation Script
Audits generated CSV datasets in data/ against all physical and statistical checks.
"""

import sys
from pathlib import Path
import pandas as pd

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.data_validation import DatasetValidator


def main():
    print("===================================================================")
    print("GRIDWISE AI - PHASE 3: DATA VALIDATION SUITE")
    print("===================================================================")
    data_dir = BASE_DIR / "data"
    proc_dir = data_dir / "processed"
    scen_dir = data_dir / "scenarios"

    demand_file = proc_dir / "campus_demand_hourly.csv"
    solar_file = proc_dir / "solar_generation_hourly.csv"
    price_file = proc_dir / "electricity_prices_hourly.csv"
    weather_file = scen_dir / "weather_scenarios_500.csv"
    combined_file = scen_dir / "combined_scenarios_500.csv"

    for f in [demand_file, solar_file, price_file, weather_file, combined_file]:
        if not f.exists():
            print(f"❌ Error: Required dataset file not found: {f}")
            print("Please run scripts/generate_dataset.py first.")
            sys.exit(1)

    print("Loading CSV datasets for validation...")
    df_demand = pd.read_csv(demand_file)
    df_solar = pd.read_csv(solar_file)
    df_price = pd.read_csv(price_file)
    df_weather = pd.read_csv(weather_file)
    df_combined = pd.read_csv(combined_file)

    validator = DatasetValidator(str(data_dir))
    report = validator.run_full_validation(
        demand_df=df_demand,
        solar_df=df_solar,
        price_df=df_price,
        weather_df=df_weather,
        combined_df=df_combined,
    )

    print("\nValidation Results:")
    for name, res in report["datasets"].items():
        symbol = "PASS" if res["passed"] else "FAIL"
        print(f"  [{symbol}] {name.upper()}")
        for check_name, check_val in res["checks"].items():
            check_sym = "[OK]" if check_val else "[ERR]"
            print(f"      {check_sym} {check_name}")
        if res["issues"]:
            for issue in res["issues"]:
                print(f"      [WARN] ISSUE: {issue}")

    print("\nOverall Status:", report["status"])
    print(f"Reports saved to {data_dir / 'reports'}")
    print("===================================================================")

    if not report["overall_passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
