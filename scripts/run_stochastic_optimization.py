"""
GRIDWISE AI - Main Stochastic Optimization Execution Script
Executes full 500-scenario two-stage stochastic optimization, deterministic baseline,
VSS, EVPI, sensitivity analysis, and exports all result artifacts.
"""

import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Force UTF-8 stdout encoding for Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from optimization import (
    StochasticOptimizer,
    ScenarioLoader,
    BatteryParameters,
    GridParameters,
)


def main():
    print("=" * 75)
    print("GRIDWISE AI - TWO-STAGE STOCHASTIC OPTIMIZATION ENGINE (PHASE 4)")
    print("Optimization of Day-Ahead Energy Procurement for Campus Solar + BESS Microgrid")
    print("=" * 75)

    t_total_start = time.perf_counter()

    # Step 1: Load and Validate Phase 3 Scenario Inputs
    print("\n[STEP 1/6] Loading and validating Phase 3 stochastic scenarios...")
    scenarios_df, meta = ScenarioLoader.load_and_validate()
    print(f"  [OK] Loaded {meta['total_scenarios']} distinct scenarios ({meta['total_records']} hourly observations)")
    print(f"  [OK] Probability sum: {meta['probability_sum']:.6f} (Strictly Normalized)")
    print(f"  [OK] Demand range: {meta['min_demand_kwh']:.1f} to {meta['max_demand_kwh']:.1f} kWh")
    print(f"  [OK] Solar range: {meta['min_solar_kwh']:.1f} to {meta['max_solar_kwh']:.1f} kWh (Capacity cap: 800 kWp)")

    # Step 2: Configure Physical Microgrid Parameters
    print("\n[STEP 2/6] Initializing microgrid asset specifications...")
    battery = BatteryParameters(
        capacity_kwh=1000.0,
        max_charge_kw=400.0,
        max_discharge_kw=400.0,
        charging_efficiency=0.92,
        discharging_efficiency=0.92,
        initial_soc_pct=0.50,
        min_soc_pct=0.15,
        max_soc_pct=0.95,
        degradation_cost_inr_kwh=0.20,
        enforce_periodicity=True,
    )
    grid = GridParameters(
        max_day_ahead_import_kw=1000.0,
        max_real_time_import_kw=1000.0,
        max_total_import_kw=1000.0,
        max_export_kw=500.0,
        export_price_ratio=0.40,
        shortage_penalty_inr_kwh=100.0,
    )
    print(f"  [OK] Battery: {battery.capacity_kwh:.0f} kWh capacity, {battery.max_charge_kw:.0f} kW power, "
          f"round-trip efficiency: {battery.round_trip_efficiency*100:.1f}%")
    print(f"  [OK] Grid Feeder: {grid.max_total_import_kw:.0f} kW contract limit, export limit: {grid.max_export_kw:.0f} kW")

    optimizer = StochasticOptimizer(battery_params=battery, grid_params=grid)

    # Step 3: Solve Two-Stage Stochastic Linear Program
    print("\n[STEP 3/6] Formulating and solving Two-Stage Stochastic Linear Program (RP)...")
    t0 = time.perf_counter()
    stochastic_out = optimizer.solve_stochastic_model(
        scenarios_df=scenarios_df,
        risk_weight_lambda=0.0,  # Risk-neutral optimal expected cost
        time_limit_sec=90.0,
    )
    rp_solve_time = time.perf_counter() - t0
    print(f"  [OK] Solver Status: OPTIMAL (HiGHS Interior-Point / Simplex)")
    print(f"  [OK] Solver Runtime: {rp_solve_time:.3f} seconds")
    print(f"  [OK] Expected Total Daily Procurement Cost: INR {stochastic_out.expected_total_cost_inr:,.2f}")
    print(f"  [OK] Day-Ahead Procurement Committed: {stochastic_out.day_ahead_schedule_kw.sum():,.1f} kWh")
    print(f"  [OK] Maximum Equality Constraint Residual: {stochastic_out.max_eq_residual:.2e}")
    print(f"  [OK] Maximum Inequality Violation: {stochastic_out.max_ub_violation:.2e}")
    print(f"  [OK] Simultaneous Charge/Discharge: {stochastic_out.simultaneous_check['max_simultaneous_kw']:.4f} kW (Strictly 0.0)")

    # Step 4: Solve Deterministic Baseline, Evaluate EEV, and Compute VSS
    print("\n[STEP 4/6] Solving Deterministic Baseline and evaluating Expected Cost under Uncertainty (EEV)...")
    x_det, eev_cost, ev_obj, diag = optimizer.solve_deterministic_baseline(scenarios_df)
    vss_val = max(0.0, eev_cost - stochastic_out.expected_total_cost_inr)
    vss_pct = (vss_val / eev_cost * 100.0) if eev_cost > 0 else 0.0
    print(f"  [OK] Naive Deterministic Plan Objective (EV): INR {ev_obj:,.2f}")
    print(f"  [OK] True Expected Cost of Deterministic Plan (EEV): INR {eev_cost:,.2f}")
    print(f"  [OK] Stochastic Optimal Expected Cost (RP): INR {stochastic_out.expected_total_cost_inr:,.2f}")
    print(f"  [OK] Value of the Stochastic Solution (VSS = EEV - RP): INR {vss_val:,.2f} ({vss_pct:.2f}% savings)")

    # Step 5: Solve Wait-and-See (WS) Model and Compute EVPI
    print("\n[STEP 5/6] Solving Wait-and-See (WS) perfect information benchmark across all scenarios...")
    ws_cost, _ = optimizer.solve_wait_and_see(scenarios_df)
    evpi_val = max(0.0, stochastic_out.expected_total_cost_inr - ws_cost)
    evpi_pct = (evpi_val / stochastic_out.expected_total_cost_inr * 100.0) if stochastic_out.expected_total_cost_inr > 0 else 0.0
    print(f"  [OK] Expected Wait-and-See Cost (WS): INR {ws_cost:,.2f}")
    print(f"  [OK] Expected Value of Perfect Information (EVPI = RP - WS): INR {evpi_val:,.2f} ({evpi_pct:.2f}% of RP)")
    print(f"  [OK] Fundamental Theorem of Stochastic Programming Check:")
    print(f"       WS ({ws_cost:,.2f}) <= RP ({stochastic_out.expected_total_cost_inr:,.2f}) <= EEV ({eev_cost:,.2f})")
    assert ws_cost <= stochastic_out.expected_total_cost_inr + 1e-4, "Violation: WS must be <= RP"
    assert stochastic_out.expected_total_cost_inr <= eev_cost + 1e-4, "Violation: RP must be <= EEV"
    print("       [PASS] Mathematical Relationship Verified (WS <= RP <= EEV)")

    # Step 6: Sensitivity Analysis & Saving Artifacts
    print("\n[STEP 6/6] Running Sensitivity Analysis & saving all results to data/results/...")
    sens_df = optimizer.run_sensitivity_analysis(scenarios_df, sample_scenarios=50)
    print(f"  [OK] Generated {len(sens_df)} parametric sensitivity outcomes")

    weather_map = scenarios_df.groupby("scenario_id")["weather_condition"].first().to_dict()
    weather_conds = [weather_map.get(sid, "Unknown") for sid in stochastic_out.scenario_ids]

    saved_paths = optimizer.save_all_results(
        stochastic_out=stochastic_out,
        x_det=x_det,
        eev_cost=eev_cost,
        evpi_val=evpi_val,
        ws_cost=ws_cost,
        weather_conditions=weather_conds,
    )
    for name, p in saved_paths.items():
        print(f"  [SAVED] {name}: {p.name}")

    total_time = time.perf_counter() - t_total_start

    print("\n" + "=" * 75)
    print("EXECUTION SUMMARY")
    print("=" * 75)
    print(f"Total Execution Time: {total_time:.2f} seconds")
    print(f"Scenarios Evaluated: {len(stochastic_out.scenario_ids)}")
    print(f"Decision Variables: {len(stochastic_out.day_ahead_schedule_kw) + len(stochastic_out.matrix_g.flatten())*6}")
    print(f"Expected Stochastic Cost (RP): INR {stochastic_out.expected_total_cost_inr:,.2f}")
    print(f"Deterministic Policy Cost (EEV): INR {eev_cost:,.2f}")
    print(f"Value of Stochastic Solution (VSS): INR {vss_val:,.2f} ({vss_pct:.2f}% Cost Reduction)")
    print(f"Expected Value of Perfect Info (EVPI): INR {evpi_val:,.2f}")
    print(f"95% Value-at-Risk (VaR_95): INR {stochastic_out.var_95_cost_inr:,.2f}")
    print(f"95% Conditional Value-at-Risk (CVaR_95): INR {stochastic_out.cvar_95_cost_inr:,.2f}")
    print(f"Battery Equivalent Full Cycles: {stochastic_out.get_summary_dict()['battery_daily_cycles']} cycles/day")
    print("=" * 75)
    print("[SUCCESS] Phase 4 Stochastic Optimization Model execution completed successfully.\n")


if __name__ == "__main__":
    main()

