# GRIDWISE AI

### Risk-Averse Stochastic Day-Ahead Energy Procurement and Battery Dispatch for an Institutional Microgrid

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask 3.x](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com/)
[![SciPy HiGHS](https://img.shields.io/badge/Solver-SciPy%20HiGHS-orange.svg)](https://scipy.org/)
[![Tests Passing](https://img.shields.io/badge/Tests-130%20Passed-brightgreen.svg)]()
[![Production Ready](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()

> **Notice:** All load demand, solar irradiance, and electricity tariff data represent calibrated hourly simulation series developed for academic evaluation, research reproducibility, and demonstration purposes.

---

## About the Project

Institutional facilities such as university campuses face a major operational hurdle in energy management: electricity procurement contracts must be committed twenty-four hours in advance under Time-of-Use tariffs, well before actual solar generation and building occupancy loads are known.

Standard energy management systems rely on a single deterministic average forecast. This approach consistently under-hedges against overcast weather and sudden demand spikes from research laboratories, resulting in expensive real-time spot market balancing penalties.

**GRIDWISE AI** addresses this challenge through a two-stage stochastic linear programming framework:
- **First Stage:** Commits firm day-ahead power purchases before weather uncertainty unfolds.
- **Second Stage:** Dynamically dispatches on-site battery storage, balances real-time deficits, and exports surplus solar generation across diverse weather scenarios.
- **Risk Mitigation:** Uses the Rockafellar-Uryasev Conditional Value-at-Risk formulation to protect the institution against severe financial losses during extreme peak-demand conditions.

---

## Microgrid Asset Configuration

The campus microgrid consists of the following physical assets:

- **Rooftop Solar PV Array:** Monocrystalline array with temperature derating and zero nighttime generation.
- **Battery Energy Storage System:** Lithium iron phosphate containerized battery skid with bi-directional inverter capability.
- **Safe Operating State of Charge:** Enforces a protective operational window to prevent deep discharge and cell overheating.
- **Daily Energy Periodicity:** Enforces terminal energy neutrality so that the battery ends each day with at least its starting energy reserve.
- **Utility Grid Connection:** Contractual substation feeder import ceiling and reverse power feed-in export limit.
- **Tariff Structure:** Three-tier Time-of-Use pricing covering off-peak, normal, and peak hours.

---

## Core Platform Features

The platform provides an enterprise web interface divided into four primary functional areas:

### Operational Dispatch
- **Overview Dashboard:** High-level executive view showing active power balance, daily spend, and asset status.
- **Energy Monitoring:** Hourly tracking of campus electrical demand, rooftop solar output, battery power flow, and feeder load.
- **Optimization Studio:** Interactive stochastic solver interface with scenario schedule ledgers and dispatch inspection.
- **Battery Management:** Dedicated state-of-charge envelope tracking, cycle utilization, and degradation monitoring.
- **Solar Analytics:** Photovoltaic yield breakdown, weather condition distribution, and self-consumption metrics.

### Decision Intelligence & Risk Management
- **Risk Management Dashboard:** Tail-risk assessment using Value-at-Risk and Conditional Value-at-Risk with an interactive risk slider.
- **Predictive Forecasting:** Machine learning models predicting building demand, solar yield, and market prices with confidence intervals.
- **Decision Intelligence Studio:** Grounded natural-language explanations explaining operational dispatch decisions.
- **Multi-Objective Pareto Analysis:** Interactive trade-off exploration balancing economic costs, grid reliance, and carbon emissions.
- **What-If Simulation Sandbox:** Isolated testing environment to evaluate battery capacity expansion and tariff changes.

### System Operations & Administration
- **System Administration:** Diagnostic health monitors for the database, solver, forecasting modules, and storage directories.
- **Background Job Manager:** Non-blocking asynchronous task execution with live status tracking.
- **Hot Database Backups:** Online point-in-time database snapshots with automated rotation.
- **Security & RBAC:** User authentication, role-based authorization, and session protection.

### Reports & Export
- **Automated PDF Reports:** Publication-quality technical audit reports generated directly from live results.
- **Tabular Data Exports:** Downloadable CSV streams for hourly schedules, scenario distributions, and sensitivity analyses.

---

## Benchmark Findings

Evaluating the stochastic model against conventional scheduling strategies demonstrates consistent operational advantages:

| Scheduling Strategy | Daily Cost (INR) | Operational Impact |
|---|---|---|
| **Deterministic Mean Plan** | INR 70,681.64 | Naive plan based on average forecasts; suffers high spot penalties during overcast periods. |
| **Two-Stage Stochastic Plan** | INR 69,540.75 | Optimal hedge across probability-weighted scenarios; preserves battery and grid bounds. |
| **Perfect Foresight Benchmark** | INR 68,070.84 | Theoretical lower bound assuming future weather conditions are known with complete certainty. |
| **Value of Stochastic Solution** | INR 1,140.89 / day | Direct daily cost savings achieved solely by accounting for stochastic weather variations. |
| **Projected Annual Savings** | INR 416,424.85 / year | Net annual utility bill reduction for the campus microgrid. |

The fundamental ordering theorem of stochastic programming holds strictly across all test cases:
`Perfect Foresight <= Stochastic Optimization <= Deterministic Planning`

---

## Installation & Setup Instructions

Follow these steps to set up and run GRIDWISE AI on your local system:

### Prerequisites
- Python 3.10 or higher
- Git
- Standard web browser (Chrome, Firefox, Safari, or Edge)

### Step 1: Clone the Repository
```bash
git clone https://github.com/campus-microgrid/gridwise-ai.git
cd gridwise-ai
```

### Step 2: Create a Virtual Environment
```bash
# On Linux or macOS
python3 -m venv venv
source venv/bin/activate

# On Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Verify Environment Readiness
Run the pre-flight verification script to confirm dependencies, solver availability, and directory permissions:
```bash
python scripts/production_check.py
```

### Step 5: Initialize the Database & Default Accounts
Create the database schema, apply table migrations, seed initial user accounts, and generate a baseline backup:
```bash
python scripts/initialize_production.py
```

---

## Running the Platform

### Local Development Server
Start the Flask web server:
```bash
python app.py
```
Open your browser and navigate to:
`http://localhost:5000`

### Default User Credentials
The system comes pre-configured with three role-based user accounts for academic evaluation:

- **Administrator:** `admin` / `GridWise@Admin2026` (Full system access, backup restoration, user management)
- **Operator:** `operator` / `Operator@2026` (Optimization execution, manual backups, operational controls)
- **Viewer:** `viewer` / `Viewer@2026` (Read-only access to all dashboards, analytics, and reports)

*Note: Change these default passwords before deploying to any production environment.*

---

## Docker Container Deployment

For containerized deployment using Docker Compose:

```bash
# Navigate to the deployment directory
cd deployment

# Build and start services in detached mode
docker-compose up -d --build

# View container logs
docker-compose logs -f app

# Stop the services
docker-compose down
```

The application will be accessible through the Nginx reverse proxy on port 80:
`http://localhost`

---

## Automated Testing

Execute the comprehensive test suite covering all modules:

```bash
python -m pytest tests/
```

The test harness validates:
- Flask application factory and blueprint routing
- Database schema, table integrity, and foreign-key constraints
- Stochastic linear programming formulation and SciPy HiGHS solver convergence
- Energy conservation and battery continuity constraints across all hours
- Machine learning forecasters and predictive intervals
- Role-based access control and session security
- Hot database backup creation, restoration, and rotation
- Technical PDF report compilation and CSV data streaming

All tests execute with a 100% pass rate.

---

## Project Documentation & Deliverables

Comprehensive academic and operational documentation is available in the repository:

- **Academic Project Report:** `reports/GRIDWISE_AI_Final_Project_Report.pdf` (Clean, human-readable academic submission report)
- **Final Presentation Slides:** `reports/GRIDWISE_AI_Final_Presentation.pptx` (Widescreen 16:9 thesis defense slide deck)
- **Demonstration Walkthrough Guide:** `docs/GRIDWISE_AI_Final_Demo_Guide.md` (Step-by-step viva presentation script)
- **Comprehensive Viva Questions & Answers:** `docs/GRIDWISE_AI_Viva_Questions.md` (Technical questions covering mathematics, physics, and software)
- **System Requirements Specification:** `docs/GRIDWISE_AI_System_Requirements.md` (Hardware, OS, and software specifications)
- **Production Operations Guide:** `docs/GRIDWISE_AI_Deployment_Guide.md` (Detailed deployment, backup, and monitoring guide)
- **Final Submission Audit:** `docs/FINAL_SUBMISSION_AUDIT.md` (Independent verification certification)

---

## License & Attribution

Developed as an academic capstone research submission for **Risk-Averse Stochastic Day-Ahead Energy Procurement and Battery Dispatch for an Institutional Microgrid**. Released under the MIT License.
