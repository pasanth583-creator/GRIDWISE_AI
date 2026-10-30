# GRIDWISE AI — PHASE 9: WHAT-IF SIMULATION LABORATORY
## Isolated Parametric Experimentation, Asset Sizing & Stress Testing

---

### 1. Isolation Architecture
The What-If Simulation Laboratory executes parametric microgrid scenarios in an isolated memory space:
- Production configuration in SQLite table `microgrid_config` remains completely untouched.
- Modifies a decoupled copy of the scenario dataset and asset boundary vectors.
- Every experiment is tagged with an isolated `experiment_uuid` and compared directly against a chosen baseline run (e.g. `PHASE8-BASELINE`).

---

### 2. Supported Parametric Levers
1. **Solar Installed Capacity ($C_{\text{PV}}$)**: Scale from $200\text{ kWp}$ to $2,500\text{ kWp}$ to evaluate campus solar expansion ROI.
2. **Battery Storage Capacity ($E_{\text{BESS}}$)**: Scale from $200\text{ kWh}$ to $3,000\text{ kWh}$ to determine optimal energy-to-power storage ratios.
3. **Battery Inverter Power ($P_{\text{BESS}}$)**: Test high C-rate (e.g. $600\text{ kW}$) vs standard ($400\text{ kW}$) power ratings.
4. **Campus Demand Scaler ($\alpha_{\text{dem}}$)**: Simulate summer recess ($-15\%$), standard semester ($1.0$), or extreme campus heatwaves ($+30\%$).
5. **Tariff Shock Scaler ($\alpha_{\text{price}}$)**: Model utility rate reductions ($-10\%$) or severe peak tariff spikes ($+50\%$).
6. **Risk Parameter ($\lambda$)**: Evaluate sensitivity from risk-neutral ($\lambda = 0$) to conservative ($\lambda = 0.5$).

---

### 3. Verification Experiment: Solar Expansion
- **Baseline Configuration**: $800\text{ kWp}$ Solar, $1,000\text{ kWh}$ BESS $\to$ Expected Daily Cost: **₹48,021.86**, CVaR 95%: **₹58,046.35**.
- **Experimental Configuration**: $1,200\text{ kWp}$ Solar ($+50\%$ PV expansion) $\to$ Expected Daily Cost: **₹42,459.64** ($\Delta\text{Cost} = -\text{₹}5,562.22 / -11.58\%$).
- **Economic Insight**: Adding $400\text{ kWp}$ of PV displaces afternoon on-peak grid purchases and charges BESS to 95% capacity without requiring morning grid charging.

