# GRIDWISE AI &mdash; System Requirements Specification

**Project Title:** Stochastic Optimization of Day-Ahead Energy Procurement for a Campus Solar + Battery Microgrid  
**Application Name:** GRIDWISE AI  
**Version:** 1.0.0 Production  

---

## 1. Hardware Requirements

### Minimum Development & Demonstration Environment
- **Processor:** Dual-Core x86_64 or ARM64 CPU (e.g. Intel Core i3 / AMD Ryzen 3 / Apple M1 or higher).
- **RAM:** 4 GB system memory (minimum 1 GB free allocated for Python process and SQLite memory buffers).
- **Disk Storage:** 2 GB available SSD or HDD storage (for repository, virtual environment, and database snapshots).
- **Display Resolution:** $1366 \times 768$ minimum screen resolution (responsive UI supports desktop, tablet, and mobile).

### Recommended Production Deployment Environment
- **Processor:** Quad-Core x86_64 CPU (Intel Xeon / AMD EPYC / AWS c6i.xlarge or equivalent).
- **RAM:** 8 GB to 16 GB ECC RAM.
- **Disk Storage:** 20 GB high-performance NVMe SSD (accommodates 100+ rotating hot database backups and telemetry logs).
- **Network Interface:** 100 Mbps or 1 Gbps continuous internet connection (for live Open-Meteo weather API sync).

---

## 2. Operating System & Runtime

| Operating System | Compatibility Status | Notes |
|---|---|---|
| **Microsoft Windows 10 / 11** | Fully Supported | Native PowerShell 5.1 / 7+ and Python 3.10+ |
| **Ubuntu Linux 20.04 / 22.04 / 24.04 LTS** | Fully Supported | Native container and systemd deployment |
| **Red Hat Enterprise Linux / Rocky Linux 9** | Fully Supported | SELinux compatible |
| **macOS 12+ (Monterey, Ventura, Sonoma)** | Fully Supported | Apple Silicon and Intel x86_64 architectures |

### Python Environment
- **Supported Python Versions:** Python 3.10, 3.11, 3.12, 3.13, 3.14.
- **Recommended Python Version:** Python 3.11 LTS.
- **Package Manager:** `pip` ($\ge 23.0$) within an isolated `venv`.

---

## 3. Software Dependencies Matrix

| Library / Module | Required Version | Functional Purpose |
|---|---|---|
| **Flask** | $\ge 3.0.0, < 4.0.0$ | Core WSGI Web Framework, routing, blueprints, session security |
| **Werkzeug** | $\ge 3.0.0, < 4.0.0$ | PBKDF2 password hashing, secure cookie serialization |
| **NumPy** | $\ge 1.26.0$ | High-speed vectorized numerical matrix computations |
| **Pandas** | $\ge 2.0.0$ | Time-series data manipulation, tabular data indexing |
| **SciPy** | $\ge 1.11.0$ | HiGHS Linear Programming optimization solver engine |
| **Scikit-Learn** | $\ge 1.3.0$ | GBDT Demand Forecaster, RF Solar Forecaster, Ridge Price Model |
| **Requests** | $\ge 2.31.0$ | Synchronous HTTP client for Open-Meteo weather API |
| **Plotly** | $\ge 5.18.0$ | Interactive web charting engine (JSON serialized figures) |
| **ReportLab** | $\ge 4.0.0$ | Academic PDF report generation (Flowables, numbered canvas) |
| **python-pptx** | $\ge 1.0.0$ | Automated PowerPoint thesis presentation generator |
| **Gunicorn** | $\ge 21.2.0$ | Production Linux multi-threaded WSGI application server |
| **Pytest** | $\ge 7.4.0$ | Automated unit, integration, and mathematical regression testing |

---

## 4. Network and External Connectivity

- **Outbound HTTP / HTTPS:** Port 443 access to `api.open-meteo.com` (for live weather telemetry at Tiruchirappalli: 10.7905°N, 78.7047°E).
- **Inbound HTTP:** Port 5000 (direct Flask/Gunicorn) or Port 80 / 443 (Nginx reverse proxy).
- **Offline Mode:** If external network access is unavailable, the system automatically engages local climatological historical simulation profiles without disruption.

