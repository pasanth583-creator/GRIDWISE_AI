# GRIDWISE AI — PHASE 9: EXPLAINABLE OPTIMIZATION
## Data-Grounded Decision Explanations for Day-Ahead Microgrid Dispatch

---

### 1. Methodology & Principle of Grounded Explanations
Explainable AI (XAI) in GRIDWISE AI avoids black-box approximations or fabricated narratives. Every explanation is mathematically linked to actual decision vectors, shadow prices, and scenario statistics:

1. **First-Stage Day-Ahead Commitments ($x_t$)**:
   - The linear program commits to forward grid procurement during hours where $\lambda_t^{\text{DA}} < \mathbb{E}[\lambda_{t,s}^{\text{RT}}]$.
   - Explains the exact percentage of campus load covered and cites peak purchasing hours.

2. **Battery Dispatch & Arbitrage Dynamics ($c_{t,s}, d_{t,s}$)**:
   - Identifies the empirical charging window (off-peak night hours $00:00$–$05:00$) and discharging window (on-peak evening hours $17:00$–$20:00$).
   - Calculates the net arbitrage spread:
     $$\Delta \lambda = \bar{\lambda}_{\text{dis}} - \bar{\lambda}_{\text{ch}} - c_{\text{deg}} - \text{Loss}_{\text{roundtrip}}$$
     Demonstrates why battery cycling delivers a net economic surplus over degradation wear.

3. **Solar PV Utilization vs Export ($e_{t,s}$)**:
   - Proves why solar self-consumption is prioritized over grid export: feed-in export tariff provides only 50% of retail purchase rates.
   - Highlights that export only occurs when battery SOC reaches its 95% ceiling buffer (950 kWh).

4. **Stochastic vs Deterministic Solution (VSS & EEV)**:
   - Explains why the deterministic Expected Value solution (EEV) suffers from under-commitment and costly real-time balancing penalties.
   - Quantifies the Value of Stochastic Solution (VSS) and Expected Value of Perfect Information (EVPI).

5. **Financial Tail Risk Posture (VaR & CVaR 95%)**:
   - Formulates the Rockafellar-Uryasev conditional expectation:
     $$\text{CVaR}_{0.95} = \min_{\alpha} \left\{ \alpha + \frac{1}{0.05} \sum_{s=1}^N p_s [C_s - \alpha]^+ \right\}$$
   - Explains tail scenario exposure under concurrent cloudy weather and peak campus demand.

---

### 2. Database Schema (`decision_explanations`)
```sql
CREATE TABLE IF NOT EXISTS decision_explanations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    explanation_uuid TEXT NOT NULL UNIQUE,
    run_uuid TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    summary_headline TEXT NOT NULL,
    detailed_explanation TEXT NOT NULL,
    key_metrics_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

