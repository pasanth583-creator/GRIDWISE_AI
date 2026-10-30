# GRIDWISE AI — PHASE 9: MULTI-OBJECTIVE OPTIMIZATION
## Weighted-Sum Linear Programming, Objective Normalization, & Cost-Only Compatibility

---

### 1. Mathematical Formulation
To address trade-offs between operating expenses, financial risk, sustainability, and battery longevity, GRIDWISE AI implements a normalized weighted-sum multi-objective formulation:

$$\min \quad w_{\text{cost}} \left(\frac{f_{\text{cost}}}{S_{\text{cost}}}\right) + w_{\text{cvar}} \left(\frac{f_{\text{cvar}}}{S_{\text{cvar}}}\right) + w_{\text{solar}} \left(\frac{f_{\text{curtail}}}{S_{\text{solar}}}\right) + w_{\text{grid}} \left(\frac{f_{\text{grid}}}{S_{\text{grid}}}\right) + w_{\text{batt}} \left(\frac{f_{\text{deg}}}{S_{\text{batt}}}\right)$$

Subject to:
- Weight normalization: $\sum_{i=1}^5 w_i = 1.0, \quad w_i \ge 0$.
- Preservation of all original physical microgrid constraints (campus energy balance, battery SOC dynamics, power ratings, and import/export limits).

#### Scaling Factors ($S_i$):
- $S_{\text{cost}} = \text{₹}50,000.0$ (baseline expected procurement cost).
- $S_{\text{cvar}} = \text{₹}60,000.0$ (baseline 95% CVaR tail cost).
- $S_{\text{solar}} = 3,500\text{ kWh} \times \text{₹}6/\text{kWh} = \text{₹}21,000.0$ (potential solar generation value).
- $S_{\text{grid}} = 7,500\text{ kWh} \times \text{₹}7/\text{kWh} = \text{₹}52,500.0$ (baseline grid energy expenditure).
- $S_{\text{batt}} = 800\text{ kWh} \times \text{₹}0.35/\text{kWh} = \text{₹}280.0$ (typical daily cell degradation wear).

---

### 2. Cost-Only Mode Compatibility
When the user configures $w_{\text{cost}} = 1.0$ and all other weights to $0.0$:
- The formulation mathematically collapses to the pure expected cost minimization of Phase 4.
- This guarantees strict backward compatibility with existing operational benchmarks and academic baselines.

