"""Loguru setup — one place to configure structured logging."""
from __future__ import annotations

import sys

from loguru import logger

from src.config import get_settings

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    settings = get_settings()
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan> - <level>{message}</level>"
        ),
        backtrace=False,
        diagnose=False,
    )
    _configured = True


__all__ = ["logger", "setup_logging"]
