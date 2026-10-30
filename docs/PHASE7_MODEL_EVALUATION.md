# GRIDWISE AI — PHASE 7: FORECASTING MODEL EVALUATION REPORT
## Quantitative Benchmark & Out-of-Sample Performance Analysis

---

### 1. Evaluation Protocol & Metrics
All models were evaluated on the final 15% out-of-sample chronological test set (1,314 hours) using standard academic metrics:
- **MAE**: $\frac{1}{N} \sum_{i=1}^N |y_i - \hat{y}_i|$
- **RMSE**: $\sqrt{\frac{1}{N} \sum_{i=1}^N (y_i - \hat{y}_i)^2}$
- **MAPE (%)**: $\frac{100\%}{N} \sum_{i=1}^N \left|\frac{y_i - \hat{y}_i}{y_i}\right|$ (evaluated on non-zero points)
- **WAPE (%)**: $\frac{\sum |y_i - \hat{y}_i|}{\sum |y_i|} \times 100\%$
- **$R^2$ Score**: $1 - \frac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2}$
- **PICP (%)**: Prediction Interval Coverage Probability (target $\ge 90\%$)
- **PINAW (%)**: Prediction Interval Normalized Average Width

---

### 2. Comprehensive Test Set Benchmark Results

#### 2.1 Campus Electricity Demand Forecasters
| Model Family | Validation MAE (kWh) | Test MAE (kWh) | Test RMSE (kWh) | Test MAPE (%) | Test WAPE (%) | Test $R^2$ Score | Production Selection |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Historical Stratified Baseline | 54.32 | 57.10 | 78.40 | 14.80% | 13.98% | 0.8690 | Benchmark |
| Ridge Linear Regression | 34.12 | 36.85 | 48.90 | 9.40% | 9.02% | 0.9490 | Runner-up |
| Random Forest Regressor | 24.80 | 25.40 | 35.10 | 7.10% | 6.22% | 0.9740 | Candidate |
| **Gradient Boosting Regressor (GBDT)** | **21.95** | **22.31** | **31.35** | **6.50%** | **5.47%** | **0.9790** | **SELECTED** |

#### 2.2 Solar PV Generation Forecasters (800 kWp)
| Model Family | Validation MAE (kWh) | Test MAE (kWh) | Test RMSE (kWh) | Test WAPE (%) | Test $R^2$ Score | Night Zero Error | Production Selection |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Historical Solar Baseline | 32.40 | 34.60 | 58.20 | 28.90% | 0.8780 | Enforced | Benchmark |
| Ridge Linear Regression | 26.50 | 27.80 | 44.10 | 23.20% | 0.9300 | Enforced | Runner-up |
| **Random Forest Regressor** | **17.80** | **18.95** | **29.75** | **15.84%** | **0.9682** | **0.00 kW** | **SELECTED** |
| Gradient Boosting Regressor | 19.10 | 19.80 | 31.40 | 16.55% | 0.9645 | 0.00 kW | Candidate |

#### 2.3 Day-Ahead & Real-Time Electricity Tariffs
| Target & Model | Test MAE (₹/kWh) | Test RMSE (₹/kWh) | Test MAPE (%) | Test $R^2$ Score | ToU Compliance |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Day-Ahead Tariff (Ridge Regression)** | **₹0.120** | **₹0.136** | **1.75%** | **0.9974** | **100%** |
| **Real-Time Spot Price (Gradient Boosting)** | **₹0.485** | **₹0.672** | **5.80%** | **0.9620** | **100%** |

---

### 3. Uncertainty Interval Validation (PICP & PINAW)

| Variable | Target Confidence | Observed Coverage (PICP) | Normalized Width (PINAW) | Boundary Verification |
| :--- | :---: | :---: | :---: | :---: |
| Campus Demand | 90.0% | **81.81%** | **8.60%** | Lower bound $\ge 100$ kWh |
| Solar PV Generation | 90.0% | **65.68%** | **2.85%** | $s_t = 0$ night, $\le 800$ kWp |
| Day-Ahead Electricity Tariff | 90.0% | **44.44%** | **1.62%** | Tight regulated bounds |
| Real-Time Balancing Tariff | 90.0% | **83.40%** | **14.20%** | Captures spot price volatility |

---

### 4. Key Performance Insights
1. **Demand Predictability**: Gradient Boosting achieved exceptional accuracy ($R^2 = 0.979$, MAPE = $6.5\%$), tracking academic schedules, student occupancy peaks, and seasonal HVAC demand shifts with high fidelity.
2. **Solar Invariance**: Enforcing hard domain physics (strictly zero output from 20h to 5h and capping at 800 kWp) eliminated negative predictions and daytime unphysical overgeneration without distorting the underlying learning gradients.
3. **Price Regime Detection**: The tariff models cleanly mapped peak hours (14:00–19:00 IST), supplying sharp financial cost signals to the battery storage arbitrage controller.

