# GRIDWISE AI

### Risk-Averse Stochastic Day-Ahead Energy Procurement and Battery Dispatch for an Institutional Microgrid

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask 3.x](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com/)
[![SciPy HiGHS](https://img.shields.io/badge/Solver-SciPy%20HiGHS-orange.svg)](https://scipy.org/)
[![Tests Passing](https://img.shields.io/badge/Tests-130%20Passed%20(100%25)-brightgreen.svg)]()
[![Production Ready](https://img.shields.io/badge/Phase%2010-Production%20Ready%20%26%20Deployed-brightgreen.svg)]()

> **NOTICE:** `SYNTHETIC SIMULATION DATA – NOT LIVE METER DATA`  
> In compliance with academic data governance standards, energy demand, solar generation, and electricity tariff time series represent calibrated synthetic simulation models combined with real-time Open-Meteo atmospheric forecasts for Tiruchirappalli Campus (10.7905°N, 78.7047°E).

---

## 1. Project Overview & Problem Statement

**GRIDWISE AI** is an enterprise-grade cyber-physical decision support and optimization platform designed for university campus microgrids. It solves the multi-horizon stochastic electricity procurement problem under volatile wholesale tariffs, intermittent rooftop photovoltaic (PV) generation, and campus occupancy demand surges.

### Physical Microgrid Assets
- **Solar Photovoltaic (PV) Array:** 800 kWp rooftop array (bifacial monocrystalline silicon with temperature derating $\gamma = -0.4\%/^\circ\text{C}$).
- **Battery Energy Storage System (BESS):** 1,000 kWh nominal capacity, 400 kW power inverter ($\eta_c = 92\%$, $\eta_d = 92\%$, round-trip $\eta_{RT} = 84.64\%$).
- **State-of-Charge (SoC) Envelope:** 10% lower bound (100 kWh safety buffer) to 90% upper bound (900 kWh ceiling).
- **Feeder Point of Common Coupling (PCC):** 1,000 kW import capacity / 500 kW export feed-in limit.
- **Geographic Coordinates:** NIT Tiruchirappalli Campus (10.7905°N, 78.7047°E).

---

## 2. Key Mathematical Results & Benchmarks

Solved using the **SciPy HiGHS linear programming solver** ($12,024$ decision variables, $14,400$ constraints in $0.42\text{ seconds}$ for 100 scenarios):

| Metric | Mathematical Description | Value (INR) | Operational Impact |
|---|---|---|---|
| **Recourse Problem (RP)** | $\min_{\mathbf{x}} \mathbb{E}[C(\mathbf{x}, \boldsymbol{\xi})]$ | **₹48,021.86 / day** | Optimal expected daily stochastic procurement cost. |
| **Deterministic Heuristic (EEV)** | $\mathbb{E}[C(\bar{\mathbf{x}}, \boldsymbol{\xi})]$ | **₹50,984.54 / day** | Expected cost of naive mean-forecast schedule under uncertainty. |
| **Wait-and-See Benchmark (WS)** | $\mathbb{E}[\min_{\mathbf{x}} C(\mathbf{x}, \boldsymbol{\xi})]$ | **₹46,816.14 / day** | Theoretical lower bound under perfect foresight oracle. |
| **Value of Stochastic Solution (VSS)** | $\text{EEV} - \text{RP}$ | **₹2,962.68 / day (5.81%)** | Direct daily financial savings from stochastic modeling. |
| **Annualized Campus Savings** | $\text{VSS} \times 365$ | **₹1,081,378.20 / year** | Net annual campus utility bill reduction. |
| **Expected Value of Perfect Info (EVPI)** | $\text{RP} - \text{WS}$ | **₹1,205.72 / day (2.51%)** | Theoretical upper limit on investment in forecasting accuracy. |
| **Value-at-Risk ($\text{VaR}_{95}$)** | $(1-\alpha)\text{-quantile}$ | **₹54,670.12** | 95th percentile worst-case cost threshold. |
| **Conditional VaR ($\text{CVaR}_{95}$)** | Tail conditional mean | **₹58,046.35** | Expected procurement cost in worst 5% disaster conditions. |
| **Fundamental Theorem Check** | $\text{WS} \le \text{RP} \le \text{EEV}$ | **Verified (Strict)** | $₹46,816.14 \le ₹48,021.86 \le ₹50,984.54$. |

---

## 3. Platform Architecture & Functional Modules

### Core Web Applications (13 Comprehensive Views)
1. **Overview Dashboard (`/dashboard`)**: Full project heading banner, 4 KPI cards, 24-hr energy balance stack, solar vs demand curve, energy source donut distribution, and TOU spend summary.
2. **Energy Monitoring (`/monitoring`)**: Active power balance formula, time filters, hourly demand curve, solar generation curve, BESS bi-directional power flow, and grid import feeder tracking.
3. **Stochastic Optimization Studio (`/optimization`)**: 10 solver configuration inputs, one-click solver trigger, decision variables ledger, and primal schedule preview.
4. **Predictive Forecasting (`/forecasting`)**: GBDT Demand Model ($R^2=0.979$), Random Forest Solar Model ($R^2=0.968$), Ridge Tariff Model ($R^2=0.997$), and prediction intervals.
5. **Live Intelligence (`/live-intelligence`)**: Open-Meteo weather integration for Tiruchirappalli, PV temperature derating, weather-sensitive HVAC load, and run-to-run delta tracking.
6. **Decision Intelligence (`/decision-intelligence`)**: Grounded Explainable AI (XAI) natural-language engine, 3D Pareto frontier optimization, What-If simulation sandbox, and electrochemical battery lifecycle analytics.
7. **Scenario Analysis (`/scenarios`)**: 500 uncertainty scenarios, Latin Hypercube Sampling across 4 weather regimes, scenario probability weights ($\sum p = 1.0$), and multi-scenario bands.
8. **Risk Management (`/risk`)**: Rockafellar-Uryasev Mean-CVaR formulation, VaR/CVaR across $\alpha \in [0.90, 0.95, 0.99]$, and an interactive risk slider ($\lambda \in [0.0, 1.0]$).
9. **Battery Management (`/battery`)**: BESS metrics, 24-hr state-of-charge envelope, charge/discharge power schedule, cycling utilization rate, and containerized skid architecture.
10. **Solar Analytics (`/solar`)**: 800 kWp PV yield metrics, weather condition distribution, self-consumption overlay, and decentralized sub-array breakdown.
11. **Cost & Savings (`/costs`)**: Stochastic vs deterministic cost comparison, VSS, EVPI, TOU window spend shares, and 30-day cumulative savings projection.
12. **Reports & Export (`/reports`)**: Downloadable 12-section technical dispatch audit PDF (ReportLab 5.x) and 5 tabular CSV streaming exports (`hourly`, `scenarios`, `baseline`, `sensitivity`, `risk`).
13. **System Administration & Telemetry (`/system`)**: Subsystem health diagnostics, thread-pool background job manager, SQLite online hot backups, and latency percentiles.

---

## 4. Production Security, RBAC & Deployment

### Role-Based Access Control (RBAC)
- **`admin` (`admin` / `GridWise@Admin2026`):** Full system control, database backups, restorations, and user administration.
- **`operator` (`operator` / `Operator@2026`):** Can trigger stochastic optimization runs, adjust risk weights, and initiate manual snapshots.
- **`viewer` (`viewer` / `Viewer@2026`):** Read-only access to monitoring dashboards, reports, and forecasts.

### Enterprise Deployment Options

#### Option A: Quick Local Launch
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run pre-flight readiness verification
python scripts/production_check.py

# 3. Initialize production database and RBAC accounts
python scripts/initialize_production.py

# 4. Start server
python app.py
```

#### Option B: Docker Compose Multi-Container Deployment
```bash
cd deployment
docker-compose up -d --build
```
Access the application on port 80: `http://localhost`

---

## 5. Automated Verification & Testing

Execute the complete 130-test regression verification suite:
```bash
python -m pytest tests/ -v
```
*Result:*
```
============================ 130 passed in 25.22s =============================
```



## 6. Project Documentation & Academic Deliverables

- **Academic PDF Report:** [`reports/GRIDWISE_AI_Final_Project_Report.pdf`](file:///reports/GRIDWISE_AI_Final_Project_Report.pdf) (7-page comprehensive academic publication).
- **Academic Presentation PPTX:** [`reports/GRIDWISE_AI_Final_Presentation.pptx`](file:///reports/GRIDWISE_AI_Final_Presentation.pptx) (12-slide professional thesis presentation).
- **Final Demonstration Guide:** [`docs/GRIDWISE_AI_Final_Demo_Guide.md`](file:///docs/GRIDWISE_AI_Final_Demo_Guide.md) (Live viva demo walkthrough script).
- **Comprehensive Viva Exam Q&A:** [`docs/GRIDWISE_AI_Viva_Questions.md`](file:///docs/GRIDWISE_AI_Viva_Questions.md) (30 rigorous technical questions with academic answers).
- **System Requirements:** [`docs/GRIDWISE_AI_System_Requirements.md`](file:///docs/GRIDWISE_AI_System_Requirements.md).
- **Production Operations Guide:** [`docs/GRIDWISE_AI_Deployment_Guide.md`](file:///docs/GRIDWISE_AI_Deployment_Guide.md).
- **Phase 10 Completion Report:** [`docs/PHASE10_COMPLETION_REPORT.md`](file:///docs/PHASE10_COMPLETION_REPORT.md).

---

## 7. License & Academic Attribution

Developed as an academic capstone research submission for **Risk-Averse Stochastic Day-Ahead Energy Procurement and Battery Dispatch for an Institutional Microgrid**. Released under the MIT License.
