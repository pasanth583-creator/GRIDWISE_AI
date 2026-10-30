"""
GRIDWISE AI - Flask Application Configurations
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory of Project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if present
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base configuration class with default settings."""

    # Project Metadata
    PROJECT_NAME = "GRIDWISE AI"
    PROJECT_TITLE = "Risk-Averse Stochastic Day-Ahead Energy Procurement and Battery Dispatch for an Institutional Microgrid"
    VERSION = "1.0.0"

    # Flask Settings
    SECRET_KEY = os.environ.get("SECRET_KEY", "gridwise-ai-development-secret-key-2026")
    TEMPLATES_AUTO_RELOAD = True
    JSON_SORT_KEYS = False

    # Server Settings
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", 5000))

    # Database Settings
    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH", str(BASE_DIR / "database" / "gridwise.db")
    )
    if not os.path.isabs(DATABASE_PATH):
        DATABASE_PATH = str(BASE_DIR / DATABASE_PATH)

    # Logging Settings
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = os.environ.get("LOG_FILE", str(BASE_DIR / "logs" / "gridwise.log"))
    if not os.path.isabs(LOG_FILE):
        LOG_FILE = str(BASE_DIR / LOG_FILE)

    # Campus Microgrid Specification Defaults (Phase 3 Reference Parameters)
    PV_RATED_CAPACITY_KW = float(os.environ.get("PV_RATED_CAPACITY_KW", 800.0))
    BESS_ENERGY_CAPACITY_KWH = float(os.environ.get("BESS_ENERGY_CAPACITY_KWH", 1000.0))
    BESS_POWER_RATED_KW = float(os.environ.get("BESS_POWER_RATED_KW", 400.0))
    BESS_EFFICIENCY_CHARGE = float(os.environ.get("BESS_EFFICIENCY_CHARGE", 0.92))
    BESS_EFFICIENCY_DISCHARGE = float(os.environ.get("BESS_EFFICIENCY_DISCHARGE", 0.92))
    BESS_INITIAL_SOC = float(os.environ.get("BESS_INITIAL_SOC", 0.50))
    BESS_MIN_SOC = float(os.environ.get("BESS_MIN_SOC", 0.15))
    BESS_MAX_SOC = float(os.environ.get("BESS_MAX_SOC", 0.95))
    GRID_IMPORT_LIMIT_KW = float(os.environ.get("GRID_IMPORT_LIMIT_KW", 1000.0))
    GRID_EXPORT_LIMIT_KW = float(os.environ.get("GRID_EXPORT_LIMIT_KW", 500.0))

    # Phase 8: Live Weather & Adaptive Intelligence Settings
    DEFAULT_LOCATION_NAME = os.environ.get("DEFAULT_LOCATION_NAME", "Tiruchirappalli, Tamil Nadu")
    DEFAULT_LATITUDE = float(os.environ.get("DEFAULT_LATITUDE", 10.7905))
    DEFAULT_LONGITUDE = float(os.environ.get("DEFAULT_LONGITUDE", 78.7047))
    OPEN_METEO_BASE_URL = os.environ.get("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
    WEATHER_CACHE_TTL_SECONDS = int(os.environ.get("WEATHER_CACHE_TTL_SECONDS", 900))  # 15 minutes



class DevelopmentConfig(Config):
    """Development environment specific configuration."""

    DEBUG = True
    TESTING = False
    LOG_LEVEL = "DEBUG"


class TestingConfig(Config):
    """Testing environment specific configuration."""

    TESTING = True
    DEBUG = True
    DATABASE_PATH = ":memory:"
    LOG_LEVEL = "WARNING"


class ProductionConfig(Config):
    """Production environment specific configuration."""

    DEBUG = False
    TESTING = False
    LOG_LEVEL = "INFO"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(env_name=None):
    """Retrieve configuration class by environment name."""
    if not env_name:
        env_name = os.environ.get("FLASK_ENV", "development").lower()
    return config_by_name.get(env_name, DevelopmentConfig)

