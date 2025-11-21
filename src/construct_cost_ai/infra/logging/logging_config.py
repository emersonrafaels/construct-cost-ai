"""Logging configuration using Loguru."""

import sys
from pathlib import Path

from loguru import logger

from construct_cost_ai.infra.config import settings


def setup_logging():
    """Configure Loguru logger based on settings."""
    # Remove default handler
    logger.remove()

    # Console handler
    log_level = settings.get("log_level", "INFO")
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )

    # File handler (if log_file is configured)
    log_file = settings.get("log_file")
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=log_level,
            rotation=settings.get("log_rotation", "10 MB"),
            retention=settings.get("log_retention", "30 days"),
            compression="zip",
            serialize=settings.get("log_format") == "json",
        )

    logger.info(f"Logging configured with level: {log_level}")
    return logger


# Initialize logging on module import
setup_logging()
