# GRIDWISE AI — PHASE 8: ADAPTIVE FORECASTING & SCENARIO GENERATION
## Physics-Based Photovoltaic Modeling, Weather-Sensitive Campus Load, & Correlated Scenarios

---

### 1. Physics-Based Photovoltaic Modeling

In Phase 8, solar forecasting transitions from purely historical autoregression to a hybrid physics-guided model:
$$P_{\text{solar}}(t) = C_{\text{installed}} \times \left(\frac{\text{GHI}(t)}{1000\text{ W/m}^2}\right) \times \eta_{\text{PR}} \times \eta_{\text{temp}}(t)$$

Where:
- $C_{\text{installed}} = 800.0\text{ kWp}$ (installed campus PV capacity).
- $\text{GHI}(t)$: Global Horizontal Irradiance retrieved from Open-Meteo in $\text{W/m}^2$.
- $\eta_{\text{PR}} = 0.82$: System Performance Ratio accounting for inverter conversion efficiency, DC/AC wiring, and dust soiling.
- $\eta_{\text{temp}}(t)$: Crystalline silicon thermal derating factor:
  $$\eta_{\text{temp}}(t) = \max\left(0.70, 1.0 - \gamma_T \cdot \max(0.0, T_{\text{cell}}(t) - 25.0^\circ\text{C})\right)$$
  where $\gamma_T = 0.004 / ^\circ\text{C}$ ($0.4\%/^\circ\text{C}$ temperature coefficient) and $T_{\text{cell}}(t) \approx T_{\text{amb}}(t) + 25 \times \frac{\text{GHI}(t)}{1000}$.

#### Hard Domain Physics:
- **Nighttime Zero Output**: $\forall h \in \{20, 21, 22, 23, 0, 1, 2, 3, 4, 5\}: P_{\text{solar}}(h) \equiv 0.00\text{ kW}$.
- **Non-Negativity**: $P_{\text{solar}}(h) \ge 0.00\text{ kW}$.
- **Inverter Capacity Ceiling**: $P_{\text{solar}}(h) \le 800.00\text{ kW}$.

---

### 2. Weather-Sensitive Campus Load Modeling

Campus electrical demand is strongly coupled with ambient temperature and humidity due to central HVAC chiller operation:
$$d_{\text{adapt}}(t) = d_{\text{base}}(t) \times \left[ 1.0 + \left(0.015 \cdot \Delta T_{\text{cool}}(t) + 0.005 \cdot \frac{\Delta \text{RH}(t)}{10}\right) \cdot \alpha_{\text{hvac}}(t) \right]$$

Where:
- $\Delta T_{\text{cool}}(t) = \max(0.0, T_{\text{ambient}}(t) - 28.0^\circ\text{C})$.
- $\Delta \text{RH}(t) = \max(0.0, \text{RH}(t) - 60.0\%)$ (latent dehumidification penalty).
- $\alpha_{\text{hvac}}(t) = 1.0$ during afternoon hours ($11:00$–$18:00$), and $0.5$ during morning/evening.

---

### 3. Adaptive Scenario Generation Engine

GRIDWISE AI generates $N \ge 100$ discrete stochastic scenarios ($s = 1, \dots, N$) representing potential realization paths over the 24-hour horizon:
1. **Weather Regime Stratification**: Scenarios are drawn across four weather classes:
   - Clear Sunny (40% prior probability, $+10\%$ solar multiplier)
   - Scattered Clouds (35% prior probability, $-5\%$ solar multiplier)
   - Overcast (15% prior probability, $-40\%$ solar multiplier)
   - Monsoon Rain (10% prior probability, $-75\%$ solar multiplier)
2. **Correlated Multivariate Shocks**: A day-level latent shock $z_{\text{day}} \sim \mathcal{N}(0, 0.04)$ establishes cross-correlation between elevated solar irradiance and reduced grid prices.
3. **Probability Normalization**: Every scenario is assigned an exact equal probability $p_s = 1/N$, guaranteeing:
   $$\sum_{s=1}^N p_s = 1.00000000$$
4. **Reproducibility**: Parameterized with a configurable integer seed (`random_seed=42`).

#### Generated Artifacts:
- `data/adaptive/live_weather_forecast.csv`
- `data/adaptive/adaptive_solar_forecast.csv`
- `data/adaptive/adaptive_demand_forecast.csv`
- `data/adaptive/adaptive_price_forecast.csv`
- `data/adaptive/adaptive_scenarios.csv`
- `data/adaptive/adaptive_scenario_summary.json`

