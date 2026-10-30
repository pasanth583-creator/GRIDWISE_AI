# GRIDWISE AI — PHASE 7: FORECASTING METHODOLOGY
## Intelligent Multi-Target Time Series Forecasting & Uncertainty Quantification

---

### 1. Executive Summary & Problem Formulation
In the day-ahead procurement problem for a campus solar + battery microgrid, decision-makers must commit to a 24-hour day-ahead procurement schedule ($x_t$) before the actual campus electricity demand ($d_{t,s}$), solar generation ($s_{t,s}$), and real-time balancing tariffs ($\lambda_{t,s}^{\text{RT}}$) are observed. 

Phase 7 introduces an automated machine learning and empirical uncertainty estimation engine that generates accurate 24-hour ahead point forecasts and probabilistic scenarios directly from the 8,760-hour synthetic simulation history without temporal look-ahead leakage.

> **SYNTHETIC SIMULATION NOTICE**: All training and test datasets originate from the verified reproducible synthetic simulation model. They reflect academic-quality stochastic physics rather than real-time telemetry from live utility meters.

---

### 2. Feature Engineering & Chronological Splitting

#### 2.1 Chronological Split Strategy
To prevent data snooping and target leakage, temporal ordering is strictly preserved:
- **Training Set (70%)**: First 6,132 hours (e.g., January 1 – mid-September). Scalers and model weights are fit exclusively on this slice.
- **Validation Set (15%)**: Subsequent 1,314 hours (mid-September – mid-November). Used for hyperparameter tuning, model selection, and empirical residual quantile extraction.
- **Test Set (15%)**: Final 1,314 hours (mid-November – December 31). Held out untouched for unbiased out-of-sample benchmarking.

#### 2.2 Feature Spaces by Target Variable
- **Campus Demand**:
  - Cyclical harmonic calendar encoding: $\sin(2\pi h / 24)$, $\cos(2\pi h / 24)$, $\sin(2\pi m / 12)$, $\cos(2\pi m / 12)$.
  - Academic calendar flags: `is_weekend`, `is_summer_vacation`, `is_exam_period`.
  - Autoregressive lags: $t-1, t-2, t-24, t-48, t-168$ (1-week persistence).
  - Rolling statistics: backward 24-hour rolling mean and standard deviation (shifted by 1 hour to prevent look-ahead leakage).
- **Solar PV Generation**:
  - Solar elevation geometry proxy: $\max\left(0, \sin\left(\pi \cdot \max(0, h - 6) / 12\right)\right)$.
  - Clear-sky theoretical envelope.
  - Lags: $t-24, t-48$ (previous days at identical solar angle).
- **Electricity Tariffs**:
  - Time-of-Day (ToU) regime indicators: On-Peak (14h–19h), Normal (6h–13h, 20h–21h), Off-Peak (22h–5h).
  - Day-ahead and real-time tariff lags: $t-24, t-168$.

---

### 3. Model Families & Selection Pipeline

For each predictive target, GRIDWISE AI trains four distinct algorithmic model families:
1. **Historical Baseline**: Stratified hour-of-day and month-of-year lookup baseline.
2. **Linear / Ridge Regression**: L2-regularized linear model providing convex, interpretable baseline coefficients.
3. **Random Forest Regressor**: Ensembles of decorrelated decision trees capturing non-linear interactions across seasonal and academic factors.
4. **Gradient Boosting Regressor (GBDT)**: Boosted shallow decision trees minimizing mean squared error with shrinkage.

#### Model Selection Rule:
The candidate model exhibiting the lowest Mean Absolute Error (MAE) and highest $R^2$ score on the validation partition is automatically designated as the production forecaster.

---

### 4. Physical Domain Constraint Enforcement

Purely statistical regression models can produce physically implausible outputs when extrapolating. GRIDWISE AI imposes rigorous post-processing domain operators:
1. **Solar Generation Constraints**:
   $$\hat{s}_t \in [0, 800\text{ kWp}]$$
   $$\hat{s}_t = 0.00\text{ kW} \quad \forall t \in \{0, 1, 2, 3, 4, 5, 20, 21, 22, 23\}$$
2. **Demand Non-Negativity**:
   $$\hat{d}_t \ge 100.0\text{ kWh} \quad \forall t$$
3. **Tariff Floor**:
   $$\hat{\lambda}_t^{\text{DA}} \ge \text{₹}1.0/\text{kWh}, \quad \hat{\lambda}_t^{\text{RT}} \ge \text{₹}1.0/\text{kWh}$$

---

### 5. Uncertainty Quantification & Scenario Generation

Point predictions $\hat{y}_t$ alone are insufficient for stochastic programming. GRIDWISE AI couples point forecasts with empirical prediction intervals:
- **Empirical Residual Quantiles**: The empirical error distribution $\epsilon = y_{\text{true}} - \hat{y}_{\text{pred}}$ is computed on out-of-sample validation data for every hour of the day:
  $$\hat{y}_{t}^{\text{lower}} = \hat{y}_t + Q_{\alpha/2}(\epsilon_t), \quad \hat{y}_{t}^{\text{upper}} = \hat{y}_t + Q_{1 - \alpha/2}(\epsilon_t)$$
  where $\alpha = 0.10$ for a 90% confidence interval.
- **Probabilistic Scenario Generation**: Correlated random perturbations around point forecasts are generated across four weather regimes (Sunny, Partly Cloudy, Cloudy, Rainy) to produce $N$ discrete stochastic scenarios ($s = 1, \dots, N$) with strictly normalized probabilities:
  $$\sum_{s=1}^N p_s = 1.0$$

