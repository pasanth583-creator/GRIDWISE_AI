"""
GRIDWISE AI - Automated Screenshot & UI Verification Engine
Captures headless browser screenshots of all 10 microgrid application views.
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Ensure UTF-8 output
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:5000"
SCREENSHOT_DIR = Path(__file__).resolve().parent / "screenshots"

PAGES = [
    ("dashboard", "01_overview_dashboard.png"),
    ("monitoring", "02_energy_monitoring.png"),
    ("optimization", "03_optimization_studio.png"),
    ("scenarios", "04_scenario_analysis.png"),
    ("risk", "05_risk_management.png"),
    ("battery", "06_battery_management.png"),
    ("solar", "07_solar_analytics.png"),
    ("costs", "08_cost_and_savings.png"),
    ("reports", "09_reports_and_export.png"),
    ("model", "10_model_information.png"),
]


def capture_all():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    print("[INIT] Starting Flask server for screenshot capture...")

    # Start Flask server
    flask_proc = subprocess.Popen([sys.executable, "app.py"])
    time.sleep(3.0)

    try:
        for route, filename in PAGES:
            target_url = f"{BASE_URL}/{route}"
            output_path = SCREENSHOT_DIR / filename
            print(f"[CAPTURE] {route} -> {filename} ...")

            cmd = [
                CHROME_PATH,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--hide-scrollbars",
                "--window-size=1440,900",
                "--virtual-time-budget=3000",
                f"--screenshot={str(output_path)}",
                target_url,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if output_path.exists() and output_path.stat().st_size > 0:
                print(f"   [OK] Success: {filename} ({output_path.stat().st_size // 1024} KB)")
            else:
                print(f"   [ERR] Failed to capture {filename}: {res.stderr}")

    finally:
        print("[STOP] Terminating Flask server...")
        flask_proc.terminate()
        flask_proc.wait()


if __name__ == "__main__":
    capture_all()
