# GRIDWISE AI — PHASE 7 DATA & FEATURE AUDIT REPORT
## Pre-Modeling Feature Verification, Temporal Granularity & Leakage Prevention Protocol

**Project Title:** Stochastic Optimization of Day-Ahead Energy Procurement for a Campus Solar + Battery Microgrid  
**Application Name:** GRIDWISE AI  
**Module:** Intelligent Energy Forecasting & Predictive Decision Support (Phase 7)  
**Audit Date:** October 30, 2026  
**Status:** AUDIT PASSED — FEATURE SET VERIFIED  
**Notice:** `SYNTHETIC SIMULATION DATA – NOT LIVE METER DATA`  

---

## 1. Executive Summary

Phase 7 introduces machine-learning and statistical time-series forecasting for campus electricity demand, solar photovoltaic generation, and electricity tariffs. To prevent data leakage and guarantee physical validity, an exhaustive pre-modeling audit of `data/processed/`, `data/scenarios/`, and feature dependencies was conducted.

The audit confirms that 8,760 continuous hourly observations (365 days, 2026 calendar year) are available with zero missing records. Chronological splitting (train, validation, test) without random shuffling is established as the strict standard for all forecasters.

---

## 2. Inventory of Historical Datasets & Available Features

### 2.1 Campus Electricity Demand (`data/processed/campus_demand_hourly.csv`)
- **Total Records:** 8,760 rows $\times$ 7 columns. Missing values: 0.
- **Available Native Columns:**
  - `timestamp`: Chronological string (`YYYY-MM-DD HH:MM:SS`), 1-hour interval.
  - `date`: Calendar date (`YYYY-MM-DD`).
  - `hour`: Integer dispatch interval ($0 \dots 23$).
  - `day_type`: Categorical (`weekday` or `weekend`).
  - `base_demand_kwh`: Underlying deterministic diurnal baseline (academic lecture peaks and night baseload).
  - `actual_demand_kwh`: Realized synthetic demand (Range: 120.00 kWh to 1,115.32 kWh).
  - `demand_uncertainty`: Stochastic residual term.
- **Derived Features Engineered for Forecasting:**
  - Autoregressive Lags: $D_{t-1}, D_{t-2}, D_{t-24}, D_{t-48}, D_{t-168}$ (1-hour, 2-hour, same-hour yesterday, same-hour 2-days ago, same-hour last week).
  - Rolling Window Statistics: Rolling 24-hour mean ($\mu_{24}$), rolling 24-hour standard deviation ($\sigma_{24}$), rolling 7-day mean ($\mu_{168}$).
  - Calendar & Cyclical Features: `day_of_week` ($0 \dots 6$), `is_weekend` ($0$ or $1$), `month` ($1 \dots 12$), `season` ($1 \dots 4$), $\sin(2\pi \cdot \text{hour}/24)$, $\cos(2\pi \cdot \text{hour}/24)$, $\sin(2\pi \cdot \text{month}/12)$, $\cos(2\pi \cdot \text{month}/12)$.

### 2.2 Solar Photovoltaic Generation (`data/processed/solar_generation_hourly.csv`)
- **Total Records:** 8,760 rows $\times$ 9 columns. Missing values: 0.
- **Available Native Columns:**
  - `timestamp`, `date`, `hour`.
  - `solar_capacity_kwp`: Installed DC nameplate capacity ($800.0\text{ kWp}$).
  - `irradiance_wm2`: Global Horizontal Irradiance ($0.0 \dots 980.0\text{ W/m}^2$).
  - `cloud_cover`: Attenuation factor ($0.0 \dots 1.0$).
  - `temperature_c`: Ambient air temperature (Celsius, $-2.5^\circ\text{C} \dots 38.4^\circ\text{C}$).
  - `weather_condition`: Categorical (`Sunny`, `Partly Cloudy`, `Cloudy`, `Rainy`).
  - `solar_generation_kwh`: Realized solar PV generation (Range: $0.00 \dots 628.04\text{ kWh}$).
- **Physical Invariants Enforced in Forecasting:**
  - Nighttime solar generation is strictly $0.00\text{ kWh}$ for hours $t \in [0, 5] \cup [20, 23]$.
  - Generation cannot exceed installed capacity ($800.0\text{ kWp}$).
  - Predictions are strictly clipped to non-negative values ($\hat{S}_t \ge 0$).
- **Derived Features Engineered for Forecasting:**
  - Solar Lags: $S_{t-24}, S_{t-48}$ (solar generation at same hour yesterday and 2-days ago; intra-day lags $t-1$ are zero at sunrise).
  - Theoretical Clear-Sky Benchmark: Geometric clear-sky cosine curve based on solar zenith angle.
  - Temperature lags and weather regime one-hot encodings.

### 2.3 Electricity Prices & Tariffs (`data/processed/electricity_prices_hourly.csv`)
- **Total Records:** 8,760 rows $\times$ 6 columns. Missing values: 0.
- **Available Native Columns:**
  - `timestamp`, `date`, `hour`.
  - `day_ahead_price_inr_kwh`: Day-ahead wholesale tariff (Range: ₹3.864 to ₹12.744/kWh).
  - `real_time_price_inr_kwh`: Volatile balancing spot price (Range: ₹2.733 to ₹18.637/kWh).
  - `price_category`: 3-Tier tariff window (`Off-Peak`, `Normal`, `Peak`).
- **Derived Features Engineered for Forecasting:**
  - Price Lags: $\pi_{t-24}, \pi_{t-48}, \pi_{t-168}$.
  - Tariff Window One-Hot Encodings: `is_peak` (14:00–20:00), `is_off_peak` (22:00–06:00), `is_normal` (06:00–14:00, 20:00–22:00).
  - Spot balancing volatility multiplier ($\pi^{RT}_t / \pi^{DA}_t$).

---

## 3. Chronological Train-Validation-Test Splitting (No Data Leakage)

To mirror real operational deployment and prevent temporal look-ahead bias:
- **No Random Shuffling:** Time series data are strictly split chronologically.
- **Data Partitions (365 days / 8,760 hours):**
  - **Training Set:** First 255 days (Hours 1 to 6,120: Jan 1 to Sep 12, ~70% of dataset).
  - **Validation Set:** Next 55 days (Hours 6,121 to 7,440: Sep 13 to Nov 6, ~15% of dataset).
  - **Test Set:** Final 55 days (Hours 7,441 to 8,760: Nov 7 to Dec 31, ~15% of dataset).
- **Leakage Prevention Protocols:**
  - Scalers (StandardScaler / MinMaxScaler) are fitted **only** on the training set.
  - Autoregressive lag features are computed chronologically before windowing.
  - Rolling statistics at time $t$ include observations only strictly prior to $t$ ($t-1$ backward).
  - Model selection is finalized exclusively on the Validation Set; the Test Set is reserved for untouched evaluation.

---

## 4. Modeling Strategy & Baseline Hierarchy

Four distinct model families will be trained, evaluated, and compared for each target:
1. **Seasonal Historical Baseline:** Persisted seasonal average conditioned on hour and day-of-week.
2. **Linear Regression:** Baseline parametric model with L2 regularization (Ridge) capturing linear seasonal trends.
3. **Random Forest Regressor:** Non-linear ensemble model capturing interactive thresholds between weather and calendar cycles.
4. **Gradient Boosting Regressor:** Sequential boosting optimizing least absolute/squared deviances for peak containment.

---

## 5. Summary of Audit Findings

- [x] All 8,760 hourly records exist across demand, solar, and price tables.
- [x] Zero missing values or null entries identified.
- [x] Meteorological features (`irradiance_wm2`, `cloud_cover`, `temperature_c`, `weather_condition`) confirmed present.
- [x] Chronological split protocol defined and verified to prevent data leakage.
- [x] Physical boundary constraints documented for post-prediction clamping.

