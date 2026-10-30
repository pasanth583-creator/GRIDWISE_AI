# GRIDWISE AI &mdash; Comprehensive Academic Viva Examination Q&A

**Project Title:** Risk-Averse Stochastic Day-Ahead Energy Procurement and Battery Dispatch for an Institutional Microgrid  
**Application Name:** GRIDWISE AI  
**Academic Level:** M.Tech / M.S. / Final Year Capstone Project Defense  
**Total Questions:** 30 Rigorous Technical Questions with Complete Academic Answers  

---

### Section 1: Problem Formulation & Microgrid Physics

#### Q1. Why is day-ahead electricity procurement formulated as a two-stage stochastic program rather than a deterministic linear program?
**Answer:** In deterministic planning, random variables (solar generation $S_t$, campus load $D_t$, real-time prices $\pi_t^{RT}$) are replaced by their expected values $\bar{S}_t, \bar{D}_t, \bar{\pi}_t^{RT}$. This ignores joint variance and tail correlations, committing forward procurement $x_t$ that consistently under-hedges or over-commits, incurring heavy penalties in the real-time balancing market. Two-stage stochastic programming models non-anticipativity: the decision maker commits first-stage day-ahead contracts $x_t$ before uncertainty is revealed, and subsequently takes scenario-dependent corrective second-stage recourses $(g_{s,t}, c_{s,t}, d_{s,t}, e_{s,t})$ once the true state of nature $s \in \Omega$ manifests.

#### Q2. What are the exact physical and operational specifications of the campus microgrid?
**Answer:**
- **Solar PV Capacity:** 800 kWp rooftop array (bifacial monocrystalline).
- **Battery Energy Storage System (BESS):** 1,000 kWh nominal capacity, 400 kW maximum continuous power.
- **State-of-Charge (SoC) Limits:** 10% lower bound (100 kWh) to 90% upper bound (900 kWh) to prevent accelerated chemical degradation.
- **Round-Trip Efficiency:** 84.64% ($\eta_c = 0.92, \eta_d = 0.92 \implies 0.92 \times 0.92 \approx 0.8464$).
- **Point of Common Coupling (PCC) Limits:** Import $\le 1,000 \text{ kW}$, Export $\le 500 \text{ kW}$.
- **Geographic Location:** NIT Tiruchirappalli campus (10.7905°N, 78.7047°E).

#### Q3. How does the battery State-of-Charge (SoC) dynamics maintain physical conservation of energy?
**Answer:** The discrete-time State-of-Charge dynamics across hourly time steps $t \in \{1,\dots,24\}$ follows:
$$b_{s,t} = b_{s,t-1} + \eta_c \cdot c_{s,t} \cdot \Delta t - \frac{1}{\eta_d} \cdot d_{s,t} \cdot \Delta t$$
where $\Delta t = 1.0\text{ h}$, $b_{s,0} = 500\text{ kWh}$ (50% initial SoC), and boundary conditions enforce:
$$b_{s,24} \ge b_{s,0} = 500\text{ kWh} \quad \forall s \in \Omega$$
ensuring no net battery depletion across daily operational cycles.

#### Q4. Why is simultaneous charging and discharging prevented, and how is it handled without introducing binary integer variables?
**Answer:** Simultaneous charging ($c_{s,t} > 0$) and discharging ($d_{s,t} > 0$) would cause fictitious round-trip energy losses ($\approx 15.36\%$). Because round-trip efficiency is strictly strictly less than 1 ($\eta_c \cdot \eta_d = 0.8464 < 1$) and marginal electricity prices are strictly positive, any optimal solution to the cost minimization objective will naturally satisfy $c_{s,t} \cdot d_{s,t} = 0$. Hence, binary complementarity variables are mathematically redundant, allowing the model to be solved as a continuous Linear Program (LP).

---

### Section 2: Mathematical Optimization & Stochastic Formulation

#### Q5. Write down the complete objective function of the Two-Stage Stochastic LP.
**Answer:**
$$\min_{x, g, c, d, b, e, u} \sum_{t=1}^{24} \pi_t^{DA} x_t + \sum_{s \in \Omega} p_s \sum_{t=1}^{24} \left[ \pi_{s,t}^{RT} g_{s,t} - \pi_{s,t}^{EXP} e_{s,t} + \omega_{deg} (c_{s,t} + d_{s,t}) + M \cdot u_{s,t} \right]$$
subject to:
1. Hourly Energy Balance: $x_t + g_{s,t} + S_{s,t} + d_{s,t} = D_{s,t} + c_{s,t} + e_{s,t} - u_{s,t}$
2. Battery SoC Evolution: $b_{s,t} = b_{s,t-1} + \eta_c c_{s,t} - \frac{1}{\eta_d} d_{s,t}$
3. Capacity & SoC Bounds: $0 \le x_t \le P_{grid}^{max}, \; 0 \le c_{s,t}, d_{s,t} \le P_{bess}^{max}, \; SoC_{min} \le b_{s,t} \le SoC_{max}$
4. Terminal SoC Constraint: $b_{s,24} \ge b_{s,0}$

#### Q6. What is the Value of the Stochastic Solution (VSS) and what does its numerical value represent?
**Answer:** The Value of the Stochastic Solution is defined as:
$$\text{VSS} = \text{EEV} - \text{RP}$$
where $\text{RP}$ (Recourse Problem) is the optimal two-stage stochastic cost (₹48,021.86), and $\text{EEV}$ is the expected cost of adopting the deterministic Expected Value solution (₹50,984.54). In our campus microgrid, $\text{VSS} = \text{₹}2,962.68\text{ / day}$ (a 5.81% direct cost savings, or ₹1,081,378 annually). It quantifies the exact financial loss incurred by ignoring stochasticity.

#### Q7. What is the Expected Value of Perfect Information (EVPI)?
**Answer:** The EVPI measures the maximum price an operator should pay for a hypothetical perfect forecasting oracle:
$$\text{EVPI} = \text{RP} - \text{WS}$$
where $\text{WS}$ (Wait-and-See) is the expected cost when day-ahead procurement decisions can be made after observing each scenario. For our system, $\text{EVPI} = \text{₹}1,205.72\text{ / day}$.

#### Q8. How is Conditional Value-at-Risk (CVaR) incorporated into the objective function?
**Answer:** Following the Rockafellar-Uryasev (2000) linear reformulation, for a confidence level $\alpha = 0.95$ and risk-weight $\lambda \in [0, 1]$:
$$\min (1 - \lambda) \mathbb{E}[C_s] + \lambda \left( \zeta + \frac{1}{1 - \alpha} \sum_{s \in \Omega} p_s v_s \right)$$
subject to:
$$v_s \ge C_s - \zeta, \quad v_s \ge 0 \quad \forall s \in \Omega$$
where $\zeta \in \mathbb{R}$ represents the Value-at-Risk ($\text{VaR}_{95}$), and $v_s$ represents the scenario tail excess loss.

#### Q9. How many variables and constraints exist in a 100-scenario LP formulation?
**Answer:** For 24 time steps and 100 scenarios:
- First-stage variables: 24 ($x_t$).
- Second-stage variables per scenario: $5 \times 24 = 120$ ($g, c, d, b, e$).
- Total decision variables: $24 + 100 \times 120 = 12,024$ variables (+ auxiliary risk variables $\zeta, v_s$).
- Linear equality & inequality constraints: $\approx 14,400$ constraints.
The SciPy HiGHS simplex/interior-point solver solves this sparse system in approximately 0.42 seconds.

---

### Section 3: Machine Learning & Predictive Forecasting

#### Q10. What machine learning algorithms power the campus forecasting module?
**Answer:**
1. **Campus Electricity Demand:** Gradient Boosting Regressor (GBDT) with temporal and weather features ($R^2 = 0.979$, $\text{RMSE} = 28.4\text{ kW}$).
2. **Solar PV Generation:** Random Forest Regressor trained on irradiance (GHI, DNI, DHI) and ambient temperature with negative cell derating ($R^2 = 0.968$, $\text{RMSE} = 22.1\text{ kW}$).
3. **Wholesale Real-Time Electricity Prices:** Ridge Regularized Regression with peak/off-peak indicators ($R^2 = 0.997$, $\text{MAE} = \text{₹}0.14\text{ / kWh}$).

#### Q11. How is data leakage prevented between training and testing sets?
**Answer:** Time-series chronological splits are enforced strictly. The first 70% of chronological records serve as training data, the subsequent 15% serve as validation, and the final 15% serve as an unseen out-of-sample test set. Feature scaling (StandardScaler) is fitted strictly on the training partition and transformed on test sets.

#### Q12. How does the physics-based solar generation model account for photovoltaic cell temperature derating?
**Answer:** Monocrystalline PV panels lose conversion efficiency as temperature rises. The effective PV output is modeled as:
$$P_{pv}(t) = P_{rated} \cdot \left(\frac{GHI(t)}{1000}\right) \cdot \left[1 - \gamma \cdot (T_{cell}(t) - 25^\circ\text{C})\right]$$
where $\gamma = 0.004 / ^\circ\text{C}$ (0.4% loss per degree Celsius above standard test conditions), and cell temperature is derived from ambient temperature $T_{amb}$ and irradiance:
$$T_{cell} = T_{amb} + GHI \cdot \left(\frac{\text{NOCT} - 20}{800}\right)$$

---

### Section 4: Live Intelligence & Explainable AI (XAI)

#### Q13. How does the live weather integration function without API key limitations?
**Answer:** The system integrates Open-Meteo's non-commercial atmospheric forecast API for Tiruchirappalli Campus (10.7905°N, 78.7047°E). To eliminate network latency and prevent IP throttling, an intelligent in-memory and disk cache with a 15-minute Time-To-Live (TTL) is implemented (`services/weather_service.py`). If the API is unreachable, the engine gracefully falls back to synthetic seasonal climatological profiles.

#### Q14. What is the role of Explainable AI (XAI) in the decision-support module?
**Answer:** Mathematical optimization outputs (e.g., $d_{s,t} = 380\text{ kW}$ at $t=18$) can appear opaque to human facility operators. The Explainability Engine (`services/explainability_service.py`) analyzes shadow prices (dual variables) and marginal cost differentials to generate grounded natural language explanations. For example:
> *"The battery is discharged at 18:00 (peak tariff ₹11.80/kWh) to avoid ₹4,484 in forward grid purchases, exploiting the energy stored during off-peak charging at 03:00 (tariff ₹3.40/kWh), yielding a net arbitrage of ₹8.40/kWh."*

#### Q15. How are multi-objective trade-offs evaluated via the Pareto Frontier?
**Answer:** The multi-objective engine optimizes across three competing dimensions:
1. Economic Cost ($f_1 = \text{Total Electricity Cost in INR}$).
2. Grid Dependence ($f_2 = \sum x_t + g_{s,t}$ in kWh).
3. Carbon Emissions ($f_3 = \text{Total Grid Purchases} \times 0.82\text{ kg CO}_2/\text{kWh}$).
The $\epsilon$-constraint and weighted-sum methods trace the non-dominated Pareto front, allowing campus sustainability executives to select their desired point on the cost-emission trade-off surface.

---

### Section 5: Software Engineering, Security & Production Deployment

#### Q16. Describe the Role-Based Access Control (RBAC) architecture.
**Answer:** RBAC is implemented in `services/security_service.py` with three distinct privilege tiers:
- **`viewer`:** Read-only access to monitoring dashboards, reports, and scenario viewers.
- **`operator`:** Can initiate stochastic optimization runs, adjust risk parameters, and trigger manual database snapshots.
- **`admin`:** Full administrative privileges, including user management, database point-in-time restoration, and system configuration.
Passwords are encrypted using Werkzeug PBKDF2 with SHA-256 and salted iterations.

#### Q17. How does the Background Job Manager handle long-running optimization tasks?
**Answer:** The `BackgroundJobManager` (`services/job_manager.py`) uses a concurrent Python `ThreadPoolExecutor` to execute 100-scenario LP solves asynchronously. Job states (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`) are persisted atomically in the SQLite `background_jobs` table, allowing web clients to poll status or receive completion events without blocking the main Flask HTTP server thread.

#### Q18. How does the Hot Database Backup mechanism prevent corruption during active writes?
**Answer:** Instead of performing simple filesystem copies (which can corrupt active SQLite WAL transactions), `BackupService` invokes SQLite's native C-level Online Backup API (`source_conn.backup(dest_conn, pages=100)`). This safely copies committed pages while concurrent transactions continue. Prior to saving, `PRAGMA integrity_check` is executed to guarantee backup integrity.

#### Q19. What security headers are applied to production HTTP responses?
**Answer:**
- `X-Content-Type-Options: nosniff` (prevents MIME-type sniffing).
- `X-Frame-Options: SAMEORIGIN` (mitigates clickjacking attacks).
- `X-XSS-Protection: 1; mode=block` (activates browser XSS filtering).
- `Referrer-Policy: strict-origin-when-cross-origin` (protects URI privacy).

#### Q20. How is containerized deployment structured?
**Answer:** The platform is configured via `deployment/docker-compose.yml` with two isolated containers:
1. **`app`:** Python 3.11-slim container running Gunicorn WSGI with 4 worker threads.
2. **`nginx`:** Reverse proxy handling static asset caching, SSL termination, and rate limiting (30 req/sec with burst buffer of 50).
Persistent Docker volumes protect the SQLite database, logs, backups, and generated reports across restarts.

---

### Section 6: Battery Degradation & Electrochemical Lifecycle

#### Q21. How is battery electrochemical degradation quantified in the analytics engine?
**Answer:** `BatteryLifecycleService` implements a Rainflow Cycle Counting algorithm on 24-hour SoC profiles to compute equivalent full cycles (EFC). Degradation is computed via the semi-empirical power-law model:
$$Q_{loss} = A \cdot \exp\left(-\frac{E_a}{R \cdot T}\right) \cdot (\text{EFC})^z$$
For our 1,000 kWh lithium iron phosphate (LFP) pack with 4,000-cycle life to 80% capacity retention, the microgrid's 0.82 daily EFC yields an estimated operational lifespan of 13.4 years.

#### Q22. How is battery wear penalized in the objective function?
**Answer:** A marginal battery degradation cost $\omega_{deg} = \text{₹}0.65\text{ / kWh}$ is assigned to every kilowatt-hour charged or discharged ($c_{s,t} + d_{s,t}$). This prevents the optimizer from cycling the battery for negligible price arbitrage (e.g. ₹0.20/kWh differences) that would cost more in cell wear than the revenue gained.

---

### Section 7: Testing, Verification & Financial Results

#### Q23. What is the scope and pass rate of the automated test suite?
**Answer:** The test suite contains over 120 automated test cases spanning unit, integration, mathematical validation, and API routes. The suite achieves a **100% pass rate** across all tests in approximately 114 seconds under `pytest`.

#### Q24. How is energy conservation mathematically verified in the test harness?
**Answer:** In `tests/test_optimization.py`, an automated assertion checks the first law of thermodynamics across all 24 hours and all scenarios:
$$|(x_t + g_{s,t} + S_{s,t} + d_{s,t}) - (D_{s,t} + c_{s,t} + e_{s,t} - u_{s,t})| < 10^{-4} \text{ kW} \quad \forall t, s$$
Any numerical deviation greater than 0.1 Watts triggers an immediate test failure.

#### Q25. What is the verified daily and annual financial impact of GRIDWISE AI?
**Answer:**
- **Baseline Deterministic Cost:** ₹50,984.54 / day (₹18.61 Million / year).
- **Stochastic Optimal Cost:** ₹48,021.86 / day (₹17.53 Million / year).
- **Net Daily Savings:** **₹2,962.68 / day**.
- **Net Annual Campus Savings:** **₹1,081,378.20 / year**.
- **Peak Demand Reduction:** 32.4% reduction in peak grid import during evening hours (17:00–21:00).
- **Solar PV Self-Consumption:** 100% (zero curtailment).

---

### Section 8: Examiner Deep-Dive & Edge Cases

#### Q26. What happens if real-time demand exceeds the grid physical import limit?
**Answer:** The shortage slack variable $u_{s,t} \ge 0$ captures any unserved load at an extreme penalty cost ($M = \text{₹}200\text{ / kWh}$). In physical operation, this triggers automated load-shedding of non-critical campus circuits (e.g., HVAC setback in administrative wings).

#### Q27. Why does the battery charge during early afternoon hours (12:00–14:00)?
**Answer:** Peak solar irradiation occurs between 11:00 and 14:00 (up to 720 kW generation), coinciding with lower classroom consumption during lunch hours. The surplus solar energy is absorbed by the BESS to prevent low-tariff grid export (₹2.50/kWh) and is held until the evening peak tariff period (18:00–21:00, ₹11.80/kWh).

#### Q28. What is the difference between Latin Hypercube Sampling (LHS) and standard Monte Carlo sampling in scenario generation?
**Answer:** Standard Monte Carlo sampling exhibits random clustering and slow $O(1/\sqrt{N})$ convergence. Latin Hypercube Sampling stratifies the probability distribution into $N$ equal probability intervals and samples exactly once from each stratum, ensuring uniform coverage across high-consequence low-probability tail events with substantially smaller scenario sizes.

#### Q29. Could this formulation handle real-time rolling re-dispatch?
**Answer:** Yes. The two-stage architecture directly extends to Receding Horizon Model Predictive Control (MPC). In real-time execution, at each hourly step $t$, the optimizer solves the remaining $24-t$ horizon with updated state-of-charge $b_{t}$ and fresh Open-Meteo weather forecasts, committing $x_{t}$ and rolling forward.

#### Q30. Why is SciPy HiGHS preferred over PuLP/CBC or commercial solvers like Gurobi?
**Answer:** HiGHS is an open-source, high-performance C++ solver included directly in SciPy ($\ge 1.9.0$) without external commercial license requirements or binary installation overhead. It provides academic-grade speed ($\approx 0.4$ seconds for 100 scenarios) and complete cross-platform reproducibility across Windows, Linux, and macOS.

