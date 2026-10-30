# GRIDWISE AI &mdash; Production Deployment & Operations Guide

**Project Title:** Stochastic Optimization of Day-Ahead Energy Procurement for a Campus Solar + Battery Microgrid  
**Application Name:** GRIDWISE AI  
**Deployment Target:** Standalone VM, Bare-Metal Server, or Docker Compose Cluster  

---

## 1. Quick Local Demonstration Setup (5 Minutes)

### Step 1: Clone and Enter Repository
```bash
git clone https://github.com/campus-microgrid/gridwise-ai.git
cd gridwise-ai
```

### Step 2: Create and Activate Virtual Environment
```bash
# On Linux / macOS:
python3 -m venv venv
source venv/bin/activate

# On Windows PowerShell:
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Run Pre-Flight Readiness Verification
```bash
python scripts/production_check.py
```
*Expected Output:*
```
[SUCCESS] System is 100% PRODUCTION READY for deployment.
```

### Step 5: Initialize Production Database & Seed RBAC Accounts
```bash
python scripts/initialize_production.py
```

### Step 6: Start Application Server
```bash
python app.py
```
Open your browser at `http://localhost:5000` to interact with GRIDWISE AI.

---

## 2. Docker Containerized Deployment

### Architecture Overview
The multi-container deployment architecture consists of:
- **`app` container:** Python 3.11-slim executing Gunicorn with 4 `gthread` workers on internal port 5000.
- **`nginx` container:** Reverse proxy providing gzip compression, rate limiting (30 req/s), security headers, and static file caching.
- **Named Docker Volumes:** Persistent storage for SQLite database, access/error logs, hot backups, and generated reports.

### Deployment Commands
```bash
# 1. Navigate to deployment directory
cd deployment

# 2. Build and launch services in background
docker-compose up -d --build

# 3. Verify container health status
docker-compose ps

# 4. Inspect real-time application logs
docker-compose logs -f app
```

Access the application on host port 80: `http://localhost`

---

## 3. Production Environment Variables (`.env`)

Copy the template before launching:
```bash
cp .env.example .env
```

Key configuration parameters in `.env`:
```ini
FLASK_ENV=production
FLASK_DEBUG=0
PORT=5000
SECRET_KEY=generate-a-strong-random-hex-key-here
DATABASE_PATH=database/gridwise.db
LOG_LEVEL=INFO
LOG_FILE=logs/gridwise.log

# Campus Microgrid Physical Parameters
SOLAR_CAPACITY_KWP=800.0
BATTERY_CAPACITY_KWH=1000.0
BATTERY_MAX_POWER_KW=400.0
BATTERY_MIN_SOC=0.10
BATTERY_MAX_SOC=0.90
BATTERY_INITIAL_SOC=0.50
BATTERY_CHARGING_EFFICIENCY=0.92
BATTERY_DISCHARGING_EFFICIENCY=0.92
GRID_IMPORT_CAPACITY_KW=1000.0
GRID_EXPORT_CAPACITY_KW=500.0
```

---

## 4. Disaster Recovery & Database Maintenance

### Creating an Online Hot Backup
To create a point-in-time snapshot without stopping write traffic:
```bash
# Via Python Service / CLI:
python -c "from services.backup_service import BackupService; print(BackupService.backup_database())"

# Via REST API (requires operator or admin credentials):
curl -X POST http://localhost:5000/api/system/backup \
     -H "Content-Type: application/json" \
     -d '{"tag": "manual_cli"}'
```

### Restoring from Backup
```bash
# Via REST API (requires admin credentials):
curl -X POST http://localhost:5000/api/system/restore \
     -H "Content-Type: application/json" \
     -d '{"filename": "gridwise_backup_20261030_130621_initial_production.db"}'
```

### Backup Rotation Policy
The backup service automatically maintains the **10 most recent backups** and purges older files to conserve disk space while preserving disaster recovery guarantees.

---

## 5. System Health Monitoring & Telemetry

| Endpoint | Method | Purpose | Response |
|---|---|---|---|
| `/health` | GET | Lightweight Liveness / Readiness Probe | HTTP 200 `{"status": "healthy"}` |
| `/api/system/health` | GET | Deep Diagnostics (DB, Solver, Models, FS) | Full Subsystem JSON Tree |
| `/api/system/metrics` | GET | Operational Telemetry (Uptime, Latency, Calls) | Histogram & Latency Percentiles |
| `/system` | GET | Web Administration Dashboard | Visual Health & Jobs Console |

