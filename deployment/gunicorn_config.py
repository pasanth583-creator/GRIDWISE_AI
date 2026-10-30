"""
GRIDWISE AI - Gunicorn Production Configuration
Configures multi-threaded WSGI worker model for high-throughput enterprise deployment.
"""

import multiprocessing
import os

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:5000")
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "gthread"
threads = int(os.getenv("GUNICORN_THREADS", 2))

# Extended timeout to accommodate 100-scenario LP solves and PDF rendering
timeout = 120
keepalive = 5

# Logging
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "logs/access.log")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "logs/error.log")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Process naming
proc_name = "gridwise_ai_app"

# Server Mechanics
daemon = False
preload_app = False

