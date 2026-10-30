# GRIDWISE AI — FINAL DEMONSTRATION WORKFLOW MANUAL
## Step-by-Step Operator Guide, Demonstration Sequence & Verification Protocol

**Project Title:** Stochastic Optimization of Day-Ahead Energy Procurement for a Campus Solar + Battery Microgrid  
**Application Name:** GRIDWISE AI  
**Author:** Principal Software Architect & Lead Systems Engineer  
**Document Purpose:** Academic Presentation, Faculty Review & System Demonstration  
**Notice:** `SYNTHETIC SIMULATION DATA – NOT LIVE METER DATA`  

---

## 1. Prerequisites and Environment Setup

Ensure Python 3.10+ (tested on Python 3.14.0 64-bit) is installed with project dependencies:

```powershell
# Navigate to the project root
cd c:\Users\A K Pasanth\OneDrive\Documents\GRIDWISE_AI

# Install all pinned dependencies (if not already installed)
pip install -r requirements.txt
```

Verify that the test suite passes 100%:
```powershell
python -m pytest tests/ -v
# Expected Output: 77 passed in ~6-8s
```

---

## 2. Step-by-Step Demonstration Sequence

### Step 1: Launch the GRIDWISE AI Platform
Start the Flask development server from the project root:
```powershell
python app.py
```
*Expected Console Output:*
```
 * Serving Flask app 'GRIDWISE AI'
 * Running on http://127.0.0.1:5000 (Press CTRL+C to quit)
```
Open a modern web browser and navigate to: **`http://127.0.0.1:5000`** (which automatically redirects to `/dashboard`).

---

### Step 2: Overview Dashboard (`/dashboard`)
1. **Visual Verification:**
   - Confirm the clean enterprise white theme (`#F8FAFC` background, green accents, professional typography).
   - Verify top header: `"STOCHASTIC OPTIMIZATION OF DAY-AHEAD ENERGY PROCUREMENT FOR A CAMPUS SOLAR + BATTERY MICROGRID"`.
   - Verify synthetic data banner: `<span class="badge">SYNTHETIC SIMULATION DATA – NOT LIVE METER DATA</span>`.
2. **Key Metric Cards:**
   - **Optimal Stochastic Cost (RP):** `₹69,540.75 / day`
   - **Value of Stochastic Solution (VSS):** `₹1,140.89 / day (1.61% savings)`
   - **Annualized Projected Savings:** `₹416,424.85 / year`
   - **Tail Risk (CVaR 95%):** `₹104,400.74`
3. **Interactive Charts:**
   - Observe the 24-hour campus net demand vs. solar generation curves.
   - Observe the hourly day-ahead procurement schedule ($3,365.5\text{ kWh}$ total).

---

### Step 3: Synthetic Dataset & Physical Parameter Audit (`/solar` and `/monitoring`)
1. Navigate to **Solar Analytics** (`/solar`):
   - Review the installed solar capacity parameter: **800 kWp**.
   - Confirm nighttime generation (20:00 to 05:00) is strictly **0.00 kW**.
   - Inspect generation profiles across the four meteorological regimes: Sunny (peak ~628 kW), Partly Cloudy, Cloudy, and Rainy.
2. Navigate to **Energy Monitoring** (`/monitoring`):
   - Inspect the real-time AC bus energy balance:
     $$x_t + g_{s,t} + S_{s,t} + d_{s,t} = D_{s,t} + c_{s,t}$$
   - Verify that equality residuals are below $10^{-12}\text{ kW}$ (strict power conservation).

---

### Step 4: Scenario Analysis Studio (`/scenarios`)
1. Click **Scenario Analysis** in the left sidebar.
2. **Scenario Matrix Verification:**
   - Total Scenarios: **500 distinct scenarios** ($12,000$ hourly observations).
   - Probability Sum: Strictly **$1.000000$** ($p_s = 0.002$ per scenario).
   - Weather Breakdown: Sunny ($35\%$), Partly Cloudy ($30\%$), Cloudy ($20\%$), Rainy ($15\%$).
3. **Interactive Visuals:**
   - Hover over the 500-scenario envelope to see solar and demand uncertainty bands.
   - Inspect the scenario probability density distribution.

---

### Step 5: Optimization Studio & Live Solver Trigger (`/optimization`)
1. Click **Optimization Studio** in the sidebar.
2. **Review Solver Configuration:**
   - Solver Engine: **SciPy HiGHS (Interior Point / Dual Simplex)**.
   - Decision Variables: **$72,024$** ($24$ first-stage, $72,000$ second-stage recourse variables).
   - Equality Constraints: **$24,000$**.
3. **Live Re-Optimization Run:**
   - Click the green **"Execute Stochastic Optimization"** button.
   - Watch the modal spinner as the HiGHS C++ solver formulates and solves the model in **~2.6 seconds**.
   - Confirm status notification: `"OPTIMAL — Solver completed successfully in 2.65s"`.

---

### Step 6: Day-Ahead Procurement & BESS Scheduling (`/battery`)
1. Navigate to **Battery Management** (`/battery`):
2. **Physical Asset Verification:**
   - BESS Energy Capacity: **$1,000\text{ kWh}$** ($400\text{ kW}$ bi-directional inverter, $0.40\text{ C}$).
   - Operational SoC Safe Window: **$15.0\%\text{ (150 kWh)}$** minimum to **$95.0\%\text{ (950 kWh)}$** ceiling.
   - Initial & Terminal Periodicity: $\text{SoC}_0 = 50.0\%$, $\text{SoC}_{24} = 50.0\%$ ($500.0\text{ kWh}$).
3. **Dispatch Schedule:**
   - Green bars indicate charging during off-peak night (01:00–05:00) and mid-day solar surplus ($857.7\text{ kWh}$ total).
   - Purple bars indicate peak-shaving discharging during evening hours 16:00–21:00 ($710.5\text{ kWh}$ total).
   - Confirm zero simultaneous charging and discharging ($\min(c_t, d_t) = 0.0000\text{ kW}$).
   - Daily Equivalent Full Cycles: **$0.86\text{ cycles/day}$** (Projected asset life $>12.5\text{ years}$).

---

### Step 7: Financial Risk Management & Interactive Pareto Slider (`/risk`)
1. Navigate to **Risk Management** (`/risk`):
2. **Tail-Risk Distribution:**
   - Expected Cost: **₹69,540.75** ($\sigma = \text{₹}17,302.32$).
   - 95% Value-at-Risk ($\text{VaR}_{95}$): **₹101,273.67**.
   - 95% Conditional Value-at-Risk ($\text{CVaR}_{95}$): **₹104,400.74**.
3. **Interactive Mean-CVaR Pareto Curve:**
   - Use the lambda selector buttons ($\lambda = 0.00, 0.25, 0.50, 0.75, 1.00$).
   - Click **$\lambda = 0.50$**:
     - Observe the highlighted red marker shift on the Plotly Pareto curve.
     - Expected Cost updates to **₹52,266.94**.
     - Tail Risk ($\text{CVaR}_{95}$) reduces to **₹62,078.13**.
     - Dynamic Hedging Premium displays: **$+₹39.55$**.
     - Tail Risk Reduction displays: **$₹95.81$**.
   - Explain the trade-off: Setting $\lambda = 0.50$ captures $55.1\%$ of maximum possible tail-risk protection for an expenditure increase of only ₹39.55/day ($+0.076\%$).

---

### Step 8: Economic Benchmarking & Savings (`/costs`)
1. Navigate to **Cost & Savings** (`/costs`):
2. **Benchmark Proof:**
   - Stochastic Optimal (RP): **₹69,540.75**
   - Deterministic Plan (EEV): **₹70,681.64**
   - Value of Stochastic Solution (VSS): **₹1,140.89 / day (1.61%)**
   - Expected Value of Perfect Information (EVPI): **₹1,469.91 / day (2.11%)**
   - Fundamental Theorem Check: $\text{WS} \le \text{RP} \le \text{EEV}$ ($₹68,070.84 \le ₹69,540.75 \le ₹70,681.64$).
3. **TOU Arbitrage Breakdown:**
   - Off-Peak (₹4.20/kWh): ₹1,698.69
   - Normal (₹7.50/kWh): ₹8,961.90
   - Peak (₹11.80/kWh): ₹8,638.55

---

### Step 9: Automated PDF Audit & CSV Data Export (`/reports`)
1. Navigate to **Reports & Export** (`/reports`):
2. **Download Technical Audit PDF:**
   - Click **"Download Technical Audit Report (PDF)"**.
   - Browser immediately downloads `GRIDWISE_AI_Dispatch_Audit.pdf` (compiled via ReportLab 5.x).
   - Open the PDF to showcase the formal 12-section technical dispatch audit.
3. **Download CSV Tabular Streams:**
   - Click each CSV export button:
     - `Hourly Dispatch Schedule (.csv)`
     - `Scenario Cost Realizations (.csv)`
     - `Deterministic vs Stochastic Baseline (.csv)`
     - `Parametric Sensitivity Results (.csv)`
     - `Risk Metrics Summary (.csv)`

---

## 3. Command-Line Demonstration Alternatives

For automated demonstration or grading scripts without opening a browser:

```powershell
# 1. Run Complete End-to-End Pipeline (Validation Mode)
python scripts/run_complete_pipeline.py --validate-only

# 2. Run Full Optimization & Report Generation
python scripts/run_complete_pipeline.py --execute-optimization --scenarios 500

# 3. Generate Submission PDF Report and Presentation PPTX
python scripts/generate_final_submission_artifacts.py

# 4. Execute Full Automated Test Suite
python -m pytest tests/ -v
```

All commands execute cleanly and output reproducible scientific benchmarks.

