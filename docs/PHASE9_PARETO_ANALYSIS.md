# GRIDWISE AI — PHASE 9: PARETO FRONTIER ANALYSIS
## Mathematical Definition of Dominance, Multi-Criteria Frontier, & Trade-Off Surface

---

### 1. Mathematical Definition of Pareto Dominance
Let $F(x) = (f_1(x), f_2(x), f_3(x), f_4(x), f_5(x))$ be the vector of objective functions evaluated for dispatch solution $x$, where:
- $f_1$: Expected Procurement Cost ($\min$)
- $f_2$: 95% CVaR Tail Risk ($\min$)
- $f_3$: Solar Self-Consumption Utilization ($\max$)
- $f_4$: Grid Energy Dependency ($\min$)
- $f_5$: Battery Degradation Wear Cost ($\min$)

A candidate dispatch solution $x^A$ **dominates** solution $x^B$ (denoted $x^A \prec x^B$) if and only if:
1. $\forall i \in \{1, 2, 4, 5\}: f_i(x^A) \le f_i(x^B)$ and $f_3(x^A) \ge f_3(x^B)$ (no worse in any objective).
2. $\exists j \in \{1, \dots, 5\}$ such that $x^A$ is strictly superior to $x^B$ in objective $j$.

A solution $x^* \in \mathcal{X}$ is **Pareto optimal** (non-dominated) if no other feasible solution $x \in \mathcal{X}$ exists such that $x \prec x^*$.

---

### 2. Evaluated Trade-Off Solutions

GRIDWISE AI evaluates sampled weight points spanning distinct operational paradigms:
1. **Cost Minimizer**: Pure expected cost minimization ($w = [1.0, 0, 0, 0, 0]$).
2. **Conservative Risk Hedged**: Heavy CVaR penalty ($w = [0.3, 0.7, 0, 0, 0]$), reducing tail volatility at the expense of a modest increase in expected day-ahead commitments.
3. **Green Solar Self-Sufficiency**: Maximum on-site PV absorption ($w = [0.3, 0.1, 0.4, 0.2, 0]$).
4. **Grid Independence**: Minimum external power purchase ($w = [0.2, 0.1, 0.2, 0.5, 0]$).
5. **Battery Conservation**: Reduced cycling wear ($w = [0.3, 0.1, 0.1, 0.1, 0.4]$).
6. **Balanced Tri-Objective**: Compromise between cost, tail risk, and green energy.

All solutions are checked pairwise for strict dominance before being flagged as `is_pareto_optimal`. Non-dominated solutions are visualized on the 2D Cost vs CVaR scatter plot with marker sizing representing battery throughput.

