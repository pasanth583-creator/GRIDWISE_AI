"""
GRIDWISE AI - Application Configuration Bridge
Re-exports configuration from config.app_config for backward compatibility.
"""

from config.app_config import (
    BASE_DIR,
    Config,
    DevelopmentConfig,
    TestingConfig,
    ProductionConfig,
    config_by_name,
    get_config,
)

__all__ = [
    "BASE_DIR",
    "Config",
    "DevelopmentConfig",
    "TestingConfig",
    "ProductionConfig",
    "config_by_name",
    "get_config",
]
