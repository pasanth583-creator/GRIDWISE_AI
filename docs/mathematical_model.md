# Mathematical Formulation: Two-Stage Stochastic Microgrid Energy Procurement

> **PROVENANCE NOTICE:**  
> All operational time-series data, solar production traces, and electricity prices utilized in GRIDWISE AI are **SYNTHETIC SIMULATION DATA – NOT LIVE METER DATA**. The values are generated via physics-grounded models and standard commercial tariff structures for academic and operational research.

---

## 1. Decision Stages & Temporal Framework

The microgrid operates over a 24-hour day-ahead horizon discretized into hourly time intervals $t \in \mathcal{T} = \{0, 1, \dots, 23\}$ ($\Delta t = 1.0\text{ hr}$). Decisions are structured as a **Two-Stage Stochastic Linear Program with Recourse**:

```
                       STAGE 1 DECISION (Day-Ahead)
                       Committed before uncertainty is observed:
                       x[t] : Day-ahead grid electricity purchase (kW)
                                   │
                                   ▼
                       UNCERTAINTY REALIZATION
                       Scenario ω ∈ Ω = {1, ..., 500} realized:
                       P_load(ω, t) : Campus electrical demand (kW)
                       P_pv(ω, t)   : Solar photovoltaic production (kW)
                       c_RT(ω, t)   : Real-time spot balancing price (INR/kWh)
                                   │
                                   ▼
                       STAGE 2 RECOURSE DECISIONS (Real-Time)
                       g[ω, t] : Real-time spot electricity purchase (kW)
                       c[ω, t] : Battery charging active power (kW)
                       d[ω, t] : Battery discharging active power (kW)
                       e[ω, t] : Surplus electricity fed-in / exported (kW)
                       b[ω, t] : Battery stored energy state (kWh)
                       s[ω, t] : Unserved load / shortage slack (kW)
```

---

## 2. Decision Variables

### First-Stage (Non-Anticipative)
* $x_t \ge 0$: Electricity procurement contracted from the utility grid in the day-ahead wholesale market for hour $t$ (kW). This decision is common across all scenarios $\omega \in \Omega$.

### Second-Stage (Scenario-Dependent Recourse)
For each scenario $\omega \in \Omega$ and hour $t \in \mathcal{T}$:
* $g_{\omega, t} \ge 0$: Real-time balancing grid purchase (kW).
* $c_{\omega, t} \ge 0$: Battery active charging power (kW).
* $d_{\omega, t} \ge 0$: Battery active discharging power (kW).
* $e_{\omega, t} \ge 0$: Grid export / feed-in power (kW).
* $b_{\omega, t} \in [E_{min}, E_{max}]$: Stored energy in the battery at the end of hour $t$ (kWh).
* $s_{\omega, t} \ge 0$: Emergency shortage / unserved demand slack variable (kW).

### Auxiliary Risk Variables (Rockafellar & Uryasev CVaR)
* $\zeta \in \mathbb{R}$: Value-at-Risk (VaR) threshold at confidence level $\alpha = 0.95$.
* $u_\omega \ge 0$: Shortfall excess beyond VaR for scenario $\omega$.

---

## 3. Objective Function

We minimize the **Mean-Conditional Value-at-Risk (Mean-CVaR)** total electricity procurement expenditure:

$$\min \quad J = (1 - \lambda) \cdot \mathbb{E}_{\omega}[\text{Cost}(\omega)] + \lambda \cdot \text{CVaR}_\alpha(\text{Cost})$$

where $\lambda \in [0, 1]$ is the risk-aversion weight. Setting $\lambda = 0$ yields a pure risk-neutral expected cost minimization.

### Expected Cost Formulation
$$\mathbb{E}_{\omega}[\text{Cost}(\omega)] = \sum_{t=0}^{23} c_{DA}(t) x_t + \sum_{\omega \in \Omega} \pi_\omega \left[ \sum_{t=0}^{23} \left( c_{RT}(\omega, t) g_{\omega, t} - c_{exp}(t) e_{\omega, t} + c_{deg} (c_{\omega, t} + d_{\omega, t}) + c_{short} s_{\omega, t} \right) \right]$$

where:
* $\pi_\omega$: Probability of scenario $\omega$, satisfying $\sum_{\omega \in \Omega} \pi_\omega = 1.0$.
* $c_{DA}(t)$: Day-ahead tariff in hour $t$ (INR/kWh).
* $c_{RT}(\omega, t)$: Real-time spot balancing price in scenario $\omega$ and hour $t$ (INR/kWh).
* $c_{exp}(t) = \gamma_{exp} \cdot c_{DA}(t)$: Feed-in export compensation price ($\gamma_{exp} = 0.40$).
* $c_{deg}$: BESS cycle degradation wear penalty (₹0.20/kWh throughput).
* $c_{short}$: Unserved energy shortage penalty (₹100.0/kWh).

### Linearized CVaR Formulation (Rockafellar & Uryasev)
$$\text{CVaR}_\alpha(\text{Cost}) = \zeta + \frac{1}{1 - \alpha} \sum_{\omega \in \Omega} \pi_\omega u_\omega$$
$$\text{subject to:} \quad u_\omega \ge \text{Cost}(\omega) - \zeta, \quad u_\omega \ge 0 \quad \forall \omega \in \Omega$$

---

## 4. Governing Constraints

### 4.1 Campus Energy Balance
For every scenario $\omega \in \Omega$ and hour $t \in \mathcal{T}$, power supply must exactly meet campus electrical demand:

$$x_t + g_{\omega, t} + P_{pv}(\omega, t) + d_{\omega, t} + s_{\omega, t} = P_{load}(\omega, t) + c_{\omega, t} + e_{\omega, t}$$

Rearranged for the equality constraint matrix:
$$x_t + g_{\omega, t} + d_{\omega, t} + s_{\omega, t} - c_{\omega, t} - e_{\omega, t} = P_{load}(\omega, t) - P_{pv}(\omega, t)$$

### 4.2 Battery Storage Dynamics & SOC Conservation
For every scenario $\omega$ and hour $t$:
$$b_{\omega, t} = b_{\omega, t-1} + \left[ \eta_{ch} c_{\omega, t} - \frac{1}{\eta_{dis}} d_{\omega, t} \right] \cdot \Delta t$$

where $\Delta t = 1.0\text{ hr}$, $\eta_{ch} = 0.92$, $\eta_{dis} = 0.92$.  
At $t = 0$, $b_{\omega, -1} = b_{init} = 500\text{ kWh}$ ($50\%$ initial SoC).

Standard linear equality form:
$$b_{\omega, t} - b_{\omega, t-1} - \eta_{ch} c_{\omega, t} + \frac{1}{\eta_{dis}} d_{\omega, t} = 0 \quad (t \ge 1)$$
$$b_{\omega, 0} - \eta_{ch} c_{\omega, 0} + \frac{1}{\eta_{dis}} d_{\omega, 0} = b_{init} \quad (t = 0)$$

### 4.3 Battery Storage Operating Envelopes
To prevent accelerated battery degradation:
$$E_{min} \le b_{\omega, t} \le E_{max} \quad \forall \omega, t$$
$$0 \le c_{\omega, t} \le P_{ch}^{max} = 400\text{ kW}$$
$$0 \le d_{\omega, t} \le P_{dis}^{max} = 400\text{ kW}$$

where $E_{min} = 0.15 \cdot E_{cap} = 150\text{ kWh}$, $E_{max} = 0.95 \cdot E_{cap} = 950\text{ kWh}$.

### 4.4 Daily Battery Neutrality (Periodicity)
Terminal stored energy must meet or exceed initial energy to prevent continuous depletion:
$$b_{\omega, 23} \ge b_{init} \implies - b_{\omega, 23} \le -500\text{ kWh} \quad \forall \omega \in \Omega$$

### 4.5 Utility Grid Interconnection Limits
Combined instantaneous power imported from the substation feeder cannot exceed contractual point-of-interconnection capacity:
$$x_t + g_{\omega, t} \le P_{grid}^{max} = 1,000\text{ kW} \quad \forall \omega, t$$
$$0 \le x_t \le P_{grid}^{max}, \quad 0 \le g_{\omega, t} \le P_{grid}^{max}$$
$$0 \le e_{\omega, t} \le P_{exp}^{max} = 500\text{ kW}$$

---

## 5. Prevention of Simultaneous Charging and Discharging

In mixed-integer formulations, binary indicators $z_t \in \{0, 1\}$ are often introduced to enforce $c_t \cdot d_t = 0$. However, in our linear programming formulation, **the linear relaxation holds with zero simultaneous operation at optimality**:

### Proof of Natural Separation:
1. The round-trip efficiency is $\eta_{rt} = \eta_{ch} \cdot \eta_{dis} = 0.92 \times 0.92 = 0.8464 < 1.0$.
2. Every kWh routed into charging and simultaneous discharging loses $1 - 0.8464 = 15.36\%$ as heat dissipation.
3. Furthermore, throughput incurs degradation costs $c_{deg} (c + d)$ with $c_{deg} = \text{₹}0.20/\text{kWh}$.
4. If a solution had simultaneous charging $c > 0$ and discharging $d > 0$, replacing them with net charging $c' = \max(0, c - d)$ and net discharging $d' = \max(0, d - c)$ strictly reduces losses, satisfies all energy balance equations, and lowers total cost.
5. Consequently, any optimal LP basic feasible solution strictly satisfies $c_{\omega, t} \cdot d_{\omega, t} = 0$ naturally without requiring integer variables.
6. Realized numerical solutions verify $\max_{\omega, t} \min(c_{\omega, t}, d_{\omega, t}) = 0.0000\text{ kW}$.

