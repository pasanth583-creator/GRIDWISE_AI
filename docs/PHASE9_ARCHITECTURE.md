# GRIDWISE AI — PHASE 9: SYSTEM ARCHITECTURE
## Explainable AI, Multi-Objective Optimization, Pareto Analysis & Decision Support

---

### 1. Architectural Overview
Phase 9 elevates GRIDWISE AI from an operational solver into an enterprise AI Decision Intelligence platform. It bridges linear programming primal and dual solution spaces with human-interpretable explanations, enables multi-criteria decision making through non-dominated Pareto frontiers, provides an isolated What-If parametric laboratory, and computes electrochemical battery lifecycle metrics.

```
                    ┌──────────────────────────────────────────────┐
                    │          User / Energy Asset Manager         │
                    └──────────────────────┬───────────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         │                                 │                                 │
         ▼                                 ▼                                 ▼
┌──────────────────┐             ┌──────────────────┐              ┌──────────────────┐
│ Explainable AI   │             │ Multi-Objective  │              │ What-If Lab      │
│ Engine           │             │ Optimization     │              │ Simulation       │
│ - LP Dual Values │             │ - Cost min       │              │ - Asset scaling  │
│ - Spread Arb.    │             │ - CVaR 95% risk  │              │ - Demand shock   │
│ - VSS / EVPI     │             │ - Solar priority │              │ - Tariff spikes  │
│ - Scenario Tail  │             │ - Battery wear   │              │ - Isolated sandbox
└────────┬─────────┘             └────────┬─────────┘              └────────┬─────────┘
         │                                │                                 │
         │                                ▼                                 │
         │                       ┌──────────────────┐                       │
         │                       │ Pareto Frontier  │                       │
         │                       │ Dominance Engine │                       │
         │                       └────────┬─────────┘                       │
         │                                │                                 │
         └────────────────────────────────┼─────────────────────────────────┘
                                          │
                                          ▼
                         ┌──────────────────────────────────┐
                         │   Two-Stage Stochastic LP Core   │
                         │       (SciPy HiGHS Solver)       │
                         └────────────────┬─────────────────┘
                                          │
                         ┌────────────────┴─────────────────┐
                         ▼                                  ▼
         ┌───────────────────────────────┐  ┌───────────────────────────────┐
         │ Battery Lifecycle Service     │  │ Recommendation Engine         │
         │ - Charge/Discharge Throughput │  │ - Prioritized Directives      │
         │ - Equivalent Full Cycles (EFC)│  │ - Supporting Metrics          │
         │ - Cycle Life Remaining (Years)│  │ - Evidence-Linked Justification
         └───────────────────────────────┘  └───────────────────────────────┘
```

---

### 2. Core Service Modules

1. **`services/explainability_service.py`**:
   - Parses primal solution vectors ($x_t, g_{t,s}, c_{t,s}, d_{t,s}, b_{t,s}, e_{t,s}$) and scenario distributions.
   - Extracts mathematical rationale for day-ahead purchasing, battery time-of-use arbitrage, solar utilization vs export, stochastic value (VSS), and tail risk exposure (VaR/CVaR).
   - Persists explanations to SQLite table `decision_explanations`.

2. **`services/multi_objective_service.py`**:
   - Implements normalized weighted-sum scalarization across 5 objectives:
     $$\min \quad w_{\text{cost}} \tilde{f}_{\text{cost}} + w_{\text{cvar}} \tilde{f}_{\text{cvar}} + w_{\text{solar}} \tilde{f}_{\text{curtail}} + w_{\text{grid}} \tilde{f}_{\text{grid}} + w_{\text{batt}} \tilde{f}_{\text{deg}}$$
   - Features a cost-only toggle that reproduces the exact Phase 4 stochastic objective.
   - Evaluates pairwise Pareto Dominance checks to identify non-dominated frontier trade-offs.

3. **`services/what_if_service.py`**:
   - Runs parametric microgrid simulations in an isolated copy of scenario data without modifying production configs.
   - Evaluates asset resizing (solar kWp, battery kWh/kW), load shifts, price shocks, and risk parameters.
   - Tracks historical experiments and comparative deltas in SQLite table `what_if_experiments`.

4. **`services/battery_lifecycle_service.py`**:
   - Calculates daily throughput (kWh), Equivalent Full Cycles (EFC), Depth-of-Discharge (DoD) swings, and degradation wear cost.
   - Projects battery lifespan remaining based on manufacturer LFP 4,500-cycle curves.

5. **`services/recommendation_service.py`**:
   - Generates prioritized operational directives across Battery Scheduling, Solar Self-Consumption, Grid Procurement, Cost Reduction, and Risk Hedging.

6. **`routes/decision_intelligence.py` & `templates/decision_intelligence.html`**:
   - Exposes 8 REST API endpoints.
   - Provides responsive enterprise UI with Plotly.js Pareto scatter plot, explanation drawers, What-If simulation forms, and battery analytics cards.

