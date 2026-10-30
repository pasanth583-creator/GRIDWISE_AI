# GRIDWISE AI &mdash; Final Demonstration & Presentation Guide

**Project Title:** Risk-Averse Stochastic Day-Ahead Energy Procurement and Battery Dispatch for an Institutional Microgrid  
**Application Name:** GRIDWISE AI  
**Academic Year:** 2026  
**Status:** Phase 10 Production Ready  

---

## 1. Executive Demonstration Overview

GRIDWISE AI is an enterprise-grade cyber-physical energy intelligence platform designed for institutional campus microgrids. It resolves the classic multi-horizon decision-making challenge: **How should a campus microgrid pre-commit day-ahead grid electricity procurement while facing stochastic real-time uncertainty in rooftop solar PV generation, building HVAC/plug loads, and volatile wholesale electricity tariffs?**

### Microgrid Physical Parameters
- **Campus Solar PV Array:** 800 kWp installed capacity (bifacial monocrystalline silicon).
- **Battery Energy Storage System (BESS):** 1,000 kWh nominal capacity, 400 kW maximum charge/discharge C-rate power.
- **Operating SoC Bounds:** 10% minimum state-of-charge ($SoC_{min} = 100 \text{ kWh}$) to 90% maximum state-of-charge ($SoC_{max} = 900 \text{ kWh}$).
- **Round-Trip Efficiency:** 84.64% ($\eta_c = 92\%$, $\eta_d = 92\%$).
- **Point of Common Coupling (PCC) Limit:** 1,000 kW import capacity, 500 kW export capacity.
- **Geographic Coordinates:** National Institute of Technology Campus, Tiruchirappalli (10.7905°N, 78.7047°E).

---

## 2. 5-Minute Live Viva Demonstration Script

### Act 1: Authentication & Role-Based Access Control (RBAC)
1. **Navigate to:** `http://localhost:5000/login`
2. **Demonstrate Roles:**
   - **Viewer Role (`viewer` / `Viewer@2026`):** Observe read-only access to monitoring dashboards, risk distributions, and forecasts. Note that administrative actions (running re-optimizations, creating hot backups) are disabled or protected with HTTP 403 Forbidden.
   - **Operator Role (`operator` / `Operator@2026`):** Switch to operator. Show access to dispatch jobs, trigger background optimizations, and create database snapshots.
   - **Admin Role (`admin` / `GridWise@Admin2026`):** Full control over users, backups, database restorations, and system configuration.

### Act 2: Stochastic Optimization & The Value of the Stochastic Solution (VSS)
1. **Navigate to:** `http://localhost:5000/optimization` (Optimization Studio).
2. **Explain the Formulation:**
   - First-stage decision: Day-ahead forward commitments $x_t \ge 0$ for $t \in \{1,\dots,24\}$.
   - Second-stage decisions: Scenario-dependent real-time purchases $g_{s,t}$, battery charging $c_{s,t}$, discharging $d_{s,t}$, and grid exports $e_{s,t}$.
   - Solver: SciPy HiGHS interior-point / dual-simplex linear solver.
3. **Show Core Benchmark Metrics:**
   - **Deterministic Expected Cost (EEV):** ₹50,984.54 / day.
   - **Two-Stage Stochastic Cost (RP):** ₹48,021.86 / day.
   - **Value of the Stochastic Solution (VSS):** **₹2,962.68 / day (5.81% direct cost reduction)**.
   - **Expected Value of Perfect Information (EVPI):** ₹1,205.72 / day (upper bound on oracle forecast value).

### Act 3: Rockafellar-Uryasev Mean-CVaR Tail-Risk Hedging
1. **Navigate to:** `http://localhost:5000/risk` (Risk Management Dashboard).
2. **Adjust the Risk Aversion Slider ($\lambda$):**
   - $\lambda = 0.0$ (Risk-Neutral): Minimizes expected cost ($\mathbb{E}[C] = \text{₹}48,021.86$), $\text{CVaR}_{95} = \text{₹}58,046.35$.
   - $\lambda = 0.5$ (Balanced Risk): Slight insurance premium paid ($+\text{₹}184.20$) to collapse 95th-percentile tail loss by $\text{₹}1,450.00$.
   - $\lambda = 1.0$ (Conservative): Full tail protection for extreme weather or price spike scenarios.

### Act 4: Live Open-Meteo Weather & Adaptive Intelligence
1. **Navigate to:** `http://localhost:5000/live-intelligence` (Live Intelligence).
2. **Highlight:**
   - Real-time weather sync for Tiruchirappalli Campus (GHI, direct normal irradiance, 2m ambient temperature, relative humidity).
   - Physics-based PV cell temperature model with negative thermal coefficient ($\gamma = -0.4\%/^\circ\text{C}$).
   - Weather-adaptive HVAC demand regression ($R^2 = 0.979$).
   - Run-to-run dispatch delta tracking and proactive grid alert thresholding.

### Act 5: Explainable AI & Multi-Objective Pareto Frontiers
1. **Navigate to:** `http://localhost:5000/decision-intelligence` (Decision Intelligence).
2. **Demonstrate 3 Decision Engines:**
   - **Explainable AI (XAI):** Natural-language grounded explanations explaining *why* the battery discharged at 18:00 (peak tariff ₹11.80/kWh) and charged at 03:00 (off-peak tariff ₹3.40/kWh).
   - **Pareto Trade-Off Surface:** Explores simultaneous minimization of Economic Cost vs. Grid Import Dependence vs. Carbon Emissions.
   - **What-If Sandbox:** Live scenario simulation allowing battery capacity expansion (+500 kWh) or tariff escalation testing without altering operational baseline data.

### Act 6: System Operations, Background Jobs & Backups
1. **Navigate to:** `http://localhost:5000/system` (System Administration).
2. **Show:**
   - Real-time Subsystem Diagnostics (Database integrity check, Solver latency, Memory telemetry).
   - Background Job Manager (Thread-pool executor with atomic status: `QUEUED` $\to$ `RUNNING` $\to$ `COMPLETED`).
   - One-click SQLite Online Hot Backup with automated 10-version rotation.

