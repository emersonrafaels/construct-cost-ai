"""Logging configuration using Loguru."""

import sys
from pathlib import Path

from loguru import logger

from construct_cost_ai.infra.config.config import get_settings

# Get settings instance
settings = get_settings()

# Get project root directory
PROJECT_ROOT = Path(__file__).parents[4].resolve()

# Create logs directory if it doesn't exist
LOG_PATH = Path(PROJECT_ROOT, "logs")
LOG_PATH.mkdir(exist_ok=True)

# Remove default logger
logger.remove()

# Get log level from settings
LOG_LEVEL = settings.get("logging.level", "INFO").upper()

# Add console logger with colors
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level=LOG_LEVEL,
)

# Add file logger for all levels (DEBUG and above)
logger.add(
    LOG_PATH / "debug_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # Create new file at midnight
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="DEBUG",
    encoding="utf-8",
)

# Add file logger for errors only
logger.add(
    LOG_PATH / "error_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="ERROR",
    encoding="utf-8",
    backtrace=True,  # Include traceback for errors
    diagnose=True,  # Include variables in traceback
)

logger.info(f"Logging configured with level: {LOG_LEVEL}")
