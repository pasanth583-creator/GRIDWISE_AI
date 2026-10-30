# GRIDWISE AI — PHASE 8: SYSTEM ARCHITECTURE
## Live Weather Integration, Adaptive Multi-Target Forecasting & Real-Time Intelligence

---

### 1. Architectural Overview
Phase 8 transforms GRIDWISE AI from a historical scenario analysis tool into an operational, adaptive day-ahead microgrid procurement platform. The platform couples live atmospheric telemetry (Open-Meteo API) with physical solar conversion models, weather-sensitive campus electrical demand modeling, and the two-stage stochastic linear programming engine.

```
                    ┌────────────────────────────┐
                    │      Open-Meteo API        │
                    │ (Tiruchirappalli, 10.79°N) │
                    └─────────────┬──────────────┘
                                  │ HTTPS GET (TTL=15m)
                                  ▼
                    ┌────────────────────────────┐
                    │       WeatherService       │
                    │  (Validation, Disk Cache,  │
                    │    Fallback Engine)        │
                    └─────────────┬──────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         │                                                 │
         ▼                                                 ▼
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     Physics-Based PV Model      │       │     Thermal HVAC Demand Model   │
│  - GHI conversion               │       │  - Temperature sensitivity      │
│  - Temperature derating         │       │  - Relative humidity latent load│
│  - Night zero invariant (20h-5h)│       │  - Academic calendar alignment  │
└────────────────┬────────────────┘       └────────────────┬────────────────┘
                 │                                         │
                 └──────────────────┬──────────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────┐
                    │ AdaptiveForecastingService  │
                    │  - Correlated Regime Shocks │
                    │  - N >= 100 Scenarios       │
                    │  - Exact Normalization (1.0)│
                    └───────────────┬─────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────┐
                    │ AdaptiveOptimizationService │
                    │  - SciPy HiGHS LP Solver    │
                    │  - First-stage DA x[t]      │
                    │  - Recourse g, c, d, e      │
                    │  - VaR & CVaR (95%)         │
                    └───────────────┬─────────────┘
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         │                                                     │
         ▼                                                     ▼
┌──────────────────────────────────┐        ┌──────────────────────────────────┐
│      AdaptiveAlertsEngine        │        │   Live Intelligence Dashboard    │
│  - Solar reduction alert         │        │  - Live weather cards (Plotly)   │
│  - Demand surge alert            │        │  - Solar vs Night horizon        │
│  - High procurement cost         │        │  - Day-ahead schedule x[t]       │
│  - CVaR risk & shift alerts      │        │  - Previous-run comparison table │
└──────────────────────────────────┘        └──────────────────────────────────┘
```

---

### 2. Core Service Modules

1. **`services/weather_service.py`**:
   - Fetches live temperature, relative humidity, cloud cover, precipitation, wind speed, and solar radiation from Open-Meteo.
   - Enforces a 15-minute caching window (in-memory + disk at `data/adaptive/weather_cache.json`).
   - Implements timeout handling, physical sanity bounds, and an offline fallback for uninterrupted operation.
   - Logs hourly observations to SQLite `weather_records`.

2. **`services/adaptive_forecasting_service.py`**:
   - Converts live GHI and ambient temperature to AC photovoltaic power using standard solar PV physics.
   - Applies chilling/HVAC thermal sensitivity to campus load ($+1.5\%/^\circ\text{C}$ above $28^\circ\text{C}$).
   - Generates $\ge 100$ correlated adaptive scenarios with normalized probabilities ($\sum p_s = 1.0$).
   - Saves CSV artifacts and persists scenario summaries to `adaptive_scenario_summaries`.

3. **`services/adaptive_optimization_service.py`**:
   - Executes two-stage stochastic linear programming (`StochasticOptimizer`).
   - Decides common first-stage day-ahead purchases $x_t$ and scenario-dependent battery recourse dispatches.
   - Calculates VaR and CVaR at 95% confidence.
   - Computes previous-run deltas ($\Delta \text{Cost}$, $\Delta \text{CVaR}$) and triggers multi-tier operational alerts.

4. **`routes/adaptive.py` & `templates/live_intelligence.html`**:
   - Exposes 9 REST endpoints for live weather, forecasting, adaptive scenario generation, and optimization.
   - Interactive enterprise UI with Plotly.js charts, KPI cards, and previous-run delta tracking.

