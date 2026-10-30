# GRIDWISE AI — PHASE 9: BATTERY LIFECYCLE & DEGRADATION ANALYTICS
## Equivalent Full Cycles, Depth-of-Discharge Swings, and Asset Degradation Costs

---

### 1. Electrochemical Assumptions & Degradation Model
The campus microgrid employs a Lithium Iron Phosphate (LFP / $\text{LiFePO}_4$) stationary battery energy storage system:
- **Nominal Capacity**: $1,000\text{ kWh}$ ($400\text{ kW}$ rated converter).
- **Rated Cycle Life**: $4,500\text{ Equivalent Full Cycles (EFC)}$ to $80\%$ remaining capacity at $80\%$ Depth-of-Discharge.
- **Calendar Shelf Life**: $15.0\text{ Years}$.
- **Degradation Wear Cost**: $\text{₹}0.35/\text{kWh}$ of throughput discharge, derived from:
  $$c_{\text{deg}} = \frac{\text{Capital Replacement Cost (₹12,000/kWh)} \times (1 - 0.80)}{4500\text{ Cycles} \times 0.80 \times 1.0\text{ kWh}} \approx \text{₹}0.35/\text{kWh}$$

> **IMPORTANT DISCLAIMER**: All degradation metrics represent engineering approximations and capacity-fade proxies for day-ahead optimization rather than warrantied physical battery degradation guarantees.

---

### 2. Formulations

1. **Daily Charge & Discharge Throughput**:
   $$E_{\text{ch}} = \sum_{t=1}^{24} c_t, \quad E_{\text{dis}} = \sum_{t=1}^{24} d_t$$
2. **Equivalent Full Cycles (EFC)**:
   $$\text{EFC} = \frac{E_{\text{dis}}}{C_{\text{nominal}}} = \frac{784.2\text{ kWh}}{1000.0\text{ kWh}} = 0.784\text{ Cycles/Day}$$
3. **Maximum Depth-of-Discharge (DoD)**:
   $$\text{DoD}_{\max} = \frac{\max_t(b_t) - \min_t(b_t)}{C_{\text{nominal}}} \times 100\% = \frac{950\text{ kWh} - 200\text{ kWh}}{1000\text{ kWh}} = 75.0\%$$
4. **Projected Lifespan**:
   $$\text{Life}_{\text{years}} = \min\left(15.0, \frac{4500\text{ Cycles}}{0.784\text{ EFC/day} \times 365.25}\right) \approx 15.0\text{ Years}$$

