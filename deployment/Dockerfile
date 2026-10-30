# ==============================================================================
# GRIDWISE AI - Production Docker Container
# Stochastic Optimization of Day-Ahead Energy Procurement Microgrid
# ==============================================================================

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=5000

# Install minimal OS dependencies for numerical packages and SQLite
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user
RUN groupadd -r gridwise && useradd -r -g gridwise -d /app -s /sbin/nologin -c "GridWise App User" gridwise

WORKDIR /app

# Install Python requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Ensure necessary directories exist and assign permissions
RUN mkdir -p /app/database /app/logs /app/backups /app/data/forecasts /app/data/results /app/reports && \
    chown -R gridwise:gridwise /app

# Switch to non-root user
USER gridwise

# Expose HTTP port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start via Gunicorn WSGI server
CMD ["gunicorn", "--config", "deployment/gunicorn_config.py", "app:app"]

