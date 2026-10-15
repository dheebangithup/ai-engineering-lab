"""
Centralized logging configuration for J.A.R.V.I.S.
Generates application and agent logs inside the workspace logs directory (workspace/logs/).
"""

from enum import Enum
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
from typing import Optional

from jarvis.workspace import default_workspace, initialize_workspace


class LogFileName(str, Enum):
    """Filenames for persisted workspace log files."""
    APP = "app.log"
    JARVIS = "jarvis.log"


class SystemLoggerName(str, Enum):
    """Standardized logger identifiers across J.A.R.V.I.S."""
    ROOT_JARVIS = "jarvis"
    SYSTEM = "jarvis.system"
    UVICORN = "uvicorn"
    UVICORN_ERROR = "uvicorn.error"
    UVICORN_ACCESS = "uvicorn.access"
    FASTAPI = "fastapi"


DEFAULT_LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | [%(name)s] %(message)s"
DEFAULT_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
DEFAULT_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB per rotated log file
DEFAULT_BACKUP_COUNT: int = 5
DEFAULT_ENCODING: str = "utf-8"

_is_configured = False


def _uncaught_exception_handler(exc_type, exc_value, exc_traceback):
    """Ensure any unhandled exception in Python is logged to app.log before exiting."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger = logging.getLogger(SystemLoggerName.SYSTEM.value)
    logger.critical(
        f"Uncaught exception: {exc_value}",
        exc_info=(exc_type, exc_value, exc_traceback),
    )


def setup_logging(
    logs_dir: Optional[Path | str] = None,
    level: int = logging.INFO,
) -> Path:
    """
    Initialize centralized logging for the J.A.R.V.I.S. platform.
    Directs log records to:
      1. <workspace>/logs/app.log (all application events, web requests, root & library logs)
      2. <workspace>/logs/jarvis.log (agent execution & reasoning traces specifically)
      3. Console (stdout)
    """
    global _is_configured

    if logs_dir is not None:
        target_logs_dir = Path(logs_dir).resolve()
    else:
        ws = initialize_workspace()
        target_logs_dir = ws.logs_dir

    target_logs_dir.mkdir(parents=True, exist_ok=True)

    app_log_path = target_logs_dir / LogFileName.APP.value
    jarvis_log_path = target_logs_dir / LogFileName.JARVIS.value

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    # 1. Main App Rotating File Handler (app.log)
    app_file_handler = RotatingFileHandler(
        str(app_log_path),
        maxBytes=DEFAULT_MAX_BYTES,
        backupCount=DEFAULT_BACKUP_COUNT,
        encoding=DEFAULT_ENCODING,
    )
    app_file_handler.setLevel(level)
    app_file_handler.setFormatter(formatter)

    # 2. Agent Trace Rotating File Handler (jarvis.log)
    jarvis_file_handler = RotatingFileHandler(
        str(jarvis_log_path),
        maxBytes=DEFAULT_MAX_BYTES,
        backupCount=DEFAULT_BACKUP_COUNT,
        encoding=DEFAULT_ENCODING,
    )
    jarvis_file_handler.setLevel(level)
    jarvis_file_handler.setFormatter(formatter)

    # 3. Console Stream Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # 4. Configure Root Logger (captures all libraries, web server, and app events into app.log)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
    root_logger.addHandler(app_file_handler)
    root_logger.addHandler(console_handler)

    # 5. Configure 'jarvis' Logger (captures agent traces into jarvis.log and propagates to root for app.log & console)
    jarvis_logger = logging.getLogger(SystemLoggerName.ROOT_JARVIS.value)
    jarvis_logger.setLevel(level)
    for h in list(jarvis_logger.handlers):
        jarvis_logger.removeHandler(h)
    jarvis_logger.addHandler(jarvis_file_handler)
    jarvis_logger.propagate = True

    # 6. Ensure Uvicorn and FastAPI loggers propagate to root
    for uv_name in (
        SystemLoggerName.UVICORN.value,
        SystemLoggerName.UVICORN_ERROR.value,
        SystemLoggerName.UVICORN_ACCESS.value,
        SystemLoggerName.FASTAPI.value,
    ):
        uv_logger = logging.getLogger(uv_name)
        uv_logger.setLevel(level)
        uv_logger.propagate = True

    # 7. Hook uncaught system exceptions
    sys.excepthook = _uncaught_exception_handler

    _is_configured = True
    jarvis_logger.info(f"Logging initialized. Application logs directed to: {app_log_path}")
    jarvis_logger.info(f"Agent execution traces directed to: {jarvis_log_path}")

    return target_logs_dir


def get_logger(name: str) -> logging.Logger:
    """
    Return a namespaced logger under 'jarvis.<name>'.
    Ensures logging is configured on first call.
    """
    global _is_configured
    if not _is_configured:
        setup_logging()

    root_prefix = f"{SystemLoggerName.ROOT_JARVIS.value}."
    if name.startswith(SystemLoggerName.ROOT_JARVIS.value):
        return logging.getLogger(name)
    return logging.getLogger(f"{root_prefix}{name}")
