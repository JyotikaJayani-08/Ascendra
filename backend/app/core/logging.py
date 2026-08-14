"""
Ascendra — Centralized Logging Configuration.

Single source of truth for log format, file handlers, and rotation policy.
Called by both the main app and the Celery worker.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

# ── Defaults ──────────────────────────────────────────────────
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5


def setup_logging(
    log_filename: str = "ascendra.log",
    level: int = logging.INFO,
) -> None:
    """
    Configure the root logger with a rotating file handler + console handler.

    Parameters
    ----------
    log_filename : str
        Name of the log file (placed in ``app/logs/``).
    level : int
        Minimum log level.
    """
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs"
    )
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_filename)

    formatter = logging.Formatter(_LOG_FORMAT)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)

    # Attach file handler if not already attached
    abs_log_path = os.path.abspath(log_path)
    has_file_handler = any(
        isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', None) == abs_log_path
        for h in root.handlers
    )
    if not has_file_handler:
        root.addHandler(file_handler)

    has_console = any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
        for h in root.handlers
    )
    if not has_console:
        root.addHandler(console_handler)
