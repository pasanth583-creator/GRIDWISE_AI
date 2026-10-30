"""
GRIDWISE AI - Battery Degradation & Lifecycle Analytics Service
Phase 9 Multi-Objective Optimization & Intelligent Decision Support

Calculates battery throughput, Equivalent Full Cycles (EFC), Depth of Discharge (DoD),
capacity fade proxies, and degradation wear costs based on actual optimization dispatch schedules.
"""

from typing import Dict, Any, Optional, List
import uuid
import numpy as np
import pandas as pd

from database.database import execute_db, query_db

class BatteryLifecycleService:
    """Computes battery degradation wear and operational lifecycle metrics."""

    # Reference LFP (Lithium Iron Phosphate) Microgrid BESS Assumptions
    CYCLE_LIFE_RATING_80_DOD = 4500  # Rated cycles to 80% capacity retention at 80% DoD
    CALENDAR_LIFE_YEARS = 15.0       # Shelf calendar life
    CELL_REPLACEMENT_COST_INR_KWH = 12000.0  # Replacement battery cost
    DEGRADATION_COST_PER_KWH = 0.35  # ₹0.35/kWh throughput (matching Phase 4 model)

    @classmethod
    def compute_lifecycle_metrics(
        cls,
        charge_kw_24h: np.ndarray,
        discharge_kw_24h: np.ndarray,
        soc_kwh_24h: np.ndarray,
        battery_capacity_kwh: float = 1000.0,
        run_uuid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculates operational lifecycle metrics from hourly dispatch schedules.

        Notice: All results represent analytical estimates and engineering proxies
        rather than warrantied electro-chemical battery life predictions.
        """
        charge_arr = np.asarray(charge_kw_24h, dtype=float)
        discharge_arr = np.asarray(discharge_kw_24h, dtype=float)
        soc_arr = np.asarray(soc_kwh_24h, dtype=float)
        cap = float(battery_capacity_kwh)

        # 1. Daily Throughput
        total_charge_kwh = float(np.sum(charge_arr))
        total_discharge_kwh = float(np.sum(discharge_arr))
        total_throughput_kwh = total_charge_kwh + total_discharge_kwh

        # 2. Equivalent Full Cycles (EFC)
        efc_daily = total_discharge_kwh / cap if cap > 0 else 0.0

        # 3. Depth of Discharge (DoD) Metrics
        min_soc = float(np.min(soc_arr)) if len(soc_arr) > 0 else 500.0
        max_soc = float(np.max(soc_arr)) if len(soc_arr) > 0 else 500.0
        max_dod_pct = float((max_soc - min_soc) / cap * 100.0) if cap > 0 else 0.0
        avg_soc_pct = float(np.mean(soc_arr) / cap * 100.0) if cap > 0 else 50.0

        # Cycle swing proxy
        daily_swings = np.abs(np.diff(soc_arr))
        avg_dod_pct = float(np.mean(daily_swings) / cap * 100.0) if len(daily_swings) > 0 else 0.0

        # 4. Battery Asset Utilization
        # Max theoretical discharge capability = 400 kW * 24h = 9600 kWh
        max_theoretical_discharge = 400.0 * 24.0
        battery_utilization_pct = (total_discharge_kwh / max_theoretical_discharge * 100.0)

        # 5. Estimated Degradation Cost
        estimated_degradation_cost = total_discharge_kwh * cls.DEGRADATION_COST_PER_KWH

        # 6. Projected Lifetime Remaining
        if efc_daily > 0.05:
            projected_cycle_life_years = round(cls.CYCLE_LIFE_RATING_80_DOD / (efc_daily * 365.25), 1)
            projected_life_years = min(cls.CALENDAR_LIFE_YEARS, projected_cycle_life_years)
        else:
            projected_life_years = cls.CALENDAR_LIFE_YEARS

        metrics_uuid = f"BATT-LIFE-{uuid.uuid4().hex[:8].upper()}"

        results = {
            "metrics_uuid": metrics_uuid,
            "run_uuid": run_uuid or f"RUN-{uuid.uuid4().hex[:6].upper()}",
            "battery_capacity_kwh": cap,
            "charge_throughput_kwh": round(total_charge_kwh, 2),
            "discharge_throughput_kwh": round(total_discharge_kwh, 2),
            "total_cycled_kwh": round(total_throughput_kwh, 2),
            "equivalent_full_cycles": round(efc_daily, 3),
            "max_dod_pct": round(max_dod_pct, 1),
            "avg_dod_pct": round(avg_dod_pct, 1),
            "avg_soc_pct": round(avg_soc_pct, 1),
            "min_soc_kwh": round(min_soc, 1),
            "max_soc_kwh": round(max_soc, 1),
            "battery_utilization_pct": round(battery_utilization_pct, 2),
            "estimated_degradation_cost_inr": round(estimated_degradation_cost, 2),
            "projected_cycle_life_remaining_years": projected_life_years,
            "disclaimer": "Analytical engineering proxy based on LFP 4500-cycle curve. Not a warrantied degradation guarantee.",
        }

        # Persist to SQLite table battery_lifecycle_metrics
        try:
            execute_db(
                """
                INSERT OR REPLACE INTO battery_lifecycle_metrics (
                    metrics_uuid, run_uuid, charge_throughput_kwh,
                    discharge_throughput_kwh, equivalent_full_cycles,
                    avg_dod_pct, max_dod_pct, battery_utilization_pct,
                    estimated_degradation_cost_inr, projected_cycle_life_remaining
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metrics_uuid,
                    results["run_uuid"],
                    results["charge_throughput_kwh"],
                    results["discharge_throughput_kwh"],
                    results["equivalent_full_cycles"],
                    results["avg_dod_pct"],
                    results["max_dod_pct"],
                    results["battery_utilization_pct"],
                    results["estimated_degradation_cost_inr"],
                    results["projected_cycle_life_remaining_years"],
                ),
            )
        except Exception:
            pass

        return results

    @classmethod
    def get_latest_lifecycle_metrics(cls) -> Dict[str, Any]:
        """Retrieves most recent lifecycle metrics or computes from latest schedule."""
        try:
            row = query_db(
                "SELECT * FROM battery_lifecycle_metrics ORDER BY created_at DESC LIMIT 1",
                one=True,
            )
            if row:
                return dict(row)
        except Exception:
            pass

        # Fallback to computing from baseline schedule
        soc_baseline = np.array([500, 500, 650, 750, 850, 850, 800, 700, 600, 500, 450, 400, 350, 350, 400, 500, 600, 450, 300, 200, 250, 350, 450, 500])
        ch_baseline = np.maximum(0, np.diff(soc_baseline, prepend=500))
        dis_baseline = np.maximum(0, -np.diff(soc_baseline, prepend=500))
        return cls.compute_lifecycle_metrics(ch_baseline, dis_baseline, soc_baseline, 1000.0)

