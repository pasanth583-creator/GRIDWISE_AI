# Campus Microgrid Technical Assumptions & System Parameters

> **PROVENANCE NOTICE:**  
> All operational time-series data, solar production traces, and electricity prices utilized in GRIDWISE AI are **SYNTHETIC SIMULATION DATA – NOT LIVE METER DATA**. The values are generated via physics-grounded models and standard commercial tariff structures for academic and operational research.

---

## 1. Physical Microgrid Asset Specifications

| Asset Parameter | Symbol | Value | Unit | Description |
|:---|:---:|:---:|:---:|:---|
| **Solar Installed Capacity** | $P_{pv}^{cap}$ | **800.0** | kWp | Total distributed rooftop & carport bifacial monocrystalline array rating |
| **BESS Nominal Energy Capacity** | $E_{bess}^{cap}$ | **1,000.0** | kWh | Containerized Lithium Iron Phosphate ($\text{LiFePO}_4$) battery system |
| **BESS Max Charging Power** | $P_{ch}^{max}$ | **400.0** | kW | Continuous bidirectional inverter charging limit (0.40 C-rate) |
| **BESS Max Discharging Power** | $P_{dis}^{max}$ | **400.0** | kW | Continuous bidirectional inverter discharging limit (0.40 C-rate) |
| **BESS Charging Efficiency** | $\eta_{ch}$ | **92.0%** | % | AC-to-DC chemical charging efficiency |
| **BESS Discharging Efficiency** | $\eta_{dis}$ | **92.0%** | % | DC-to-AC chemical discharging efficiency |
| **Round-Trip Efficiency** | $\eta_{rt}$ | **84.64%** | % | Net round-trip efficiency ($\eta_{ch} \cdot \eta_{dis} = 0.92 \times 0.92$) |
| **Initial Battery State of Charge** | $SoC_0$ | **50.0%** | % | Reference energy storage at $t=0$ ($500.0\text{ kWh}$) |
| **Minimum Operating SoC** | $SoC_{min}$ | **15.0%** | % | Deep discharge protection buffer ($150.0\text{ kWh}$) |
| **Maximum Operating SoC** | $SoC_{max}$ | **95.0%** | % | Overcharge cell protection buffer ($950.0\text{ kWh}$) |
| **BESS Degradation Cost** | $c_{deg}$ | **0.20** | INR/kWh | Cell wear wear-and-tear replacement penalty per kWh throughput |
| **Grid Point-of-Interconnection** | $P_{grid}^{max}$ | **1,000.0** | kW | Substation feeder contractual maximum import envelope |
| **Grid Reverse Power Feed-in** | $P_{exp}^{max}$ | **500.0** | kW | Contractual reverse power export limit to distribution network |
| **Export Compensation Ratio** | $\gamma_{exp}$ | **0.40** | &mdash; | Feed-in export tariff credit as fraction of day-ahead price |
| **Shortage Penalty Rate** | $c_{short}$ | **100.0** | INR/kWh | Value of lost load / slack penalty ensuring continuous feasibility |
| **Day-Ahead Planning Horizon** | $T$ | **24.0** | hours | Optimization horizon (00:00 to 23:00) |
| **Discretization Step** | $\Delta t$ | **1.0** | hour | Dispatch planning interval |

---

## 2. Simulated Electricity Tariff Structure

Reflective of standard university commercial tariffs in the Indian wholesale electricity market:

| Tariff Rating Tier | Applicable Hours (IST) | Day-Ahead Rate ($c_{DA}$) | Real-Time Spot Mean ($c_{RT}$) |
|:---|:---:|:---:|:---:|
| **Off-Peak** | 22:00 &ndash; 06:00 (Night base) | **₹4.20 / kWh** | ₹4.45 / kWh |
| **Normal (Shoulder)** | 06:00 &ndash; 14:00, 20:00 &ndash; 22:00 | **₹7.50 / kWh** | ₹7.85 / kWh |
| **On-Peak** | 14:00 &ndash; 20:00 (Campus cooling surge) | **₹11.80 / kWh** | ₹12.65 / kWh |

---

## 3. Stochastic Uncertainty Scenarios

DISCRETE SCENARIO CLASSIFICATION ($N = 500$ Scenarios):

| Weather Category | Probability ($\pi_\omega$) | Scenario Count | Solar Irradiance Multiplier | Cloud Cover Range |
|:---|:---:|:---:|:---:|:---:|
| **Sunny (Clear Sky)** | **0.3500** | 175 | 1.00x &ndash; 1.08x | 0% &ndash; 15% |
| **Partly Cloudy** | **0.3000** | 150 | 0.75x &ndash; 0.90x | 25% &ndash; 55% |
| **Cloudy (Overcast)** | **0.2000** | 100 | 0.40x &ndash; 0.60x | 65% &ndash; 85% |
| **Rainy (Storm / Rain)** | **0.1500** | 75 | 0.12x &ndash; 0.28x | 90% &ndash; 100% |
| **TOTAL** | **1.000000** | **500** | &mdash; | &mdash; |

* **Autoregressive Demand Uncertainty:** Campus load realizations follow an $\text{AR}(1)$ temporal correlation process ($\rho = 0.65$) with $\pm 15\%$ dispersion.

