"""
GRIDWISE AI - Production Logging Service
Provides structured logging, rotating file handlers, and context-aware request logging.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask import has_request_context, request, g

class RequestContextFilter(logging.Filter):
    """Augments log records with HTTP request details when in request context."""
    def filter(self, record):
        if has_request_context():
            record.ip = request.remote_addr or "127.0.0.1"
            record.method = request.method
            record.path = request.path
            record.user = getattr(g, "current_user", "anonymous")
        else:
            record.ip = "-"
            record.method = "-"
            record.path = "-"
            record.user = "system"
        return True


def setup_logger(name: str = "gridwise", log_dir: str = "logs", log_level: int = logging.INFO) -> logging.Logger:
    """Configures structured rotating file logger and stream logger."""
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    if logger.handlers:
        return logger  # Already configured
        
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] [%(user)s@%(ip)s %(method)s %(path)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    ctx_filter = RequestContextFilter()
    
    # 1. Rotating File Handler (5 MB, max 5 backups)
    log_file = os.path.join(log_dir, "gridwise.log")
    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(ctx_filter)
    logger.addHandler(file_handler)
    
    # 2. Console / Stream Handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(ctx_filter)
    logger.addHandler(stream_handler)
    
    return logger

app_logger = setup_logger()

