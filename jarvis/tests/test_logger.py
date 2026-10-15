import logging
from pathlib import Path
import pytest

from jarvis.logger import get_logger, setup_logging


def test_setup_logging_creates_files(tmp_path: Path):
    logs_dir = tmp_path / "logs"
    setup_logging(logs_dir=logs_dir)

    assert logs_dir.exists()
    app_log = logs_dir / "app.log"
    jarvis_log = logs_dir / "jarvis.log"

    assert app_log.exists()
    assert jarvis_log.exists()


def test_logger_writes_to_both_files(tmp_path: Path):
    logs_dir = tmp_path / "test_logs"
    setup_logging(logs_dir=logs_dir)

    test_logger = get_logger("test_module")
    test_message = "Test message for J.A.R.V.I.S. logger verification"
    test_logger.info(test_message)

    app_log = logs_dir / "app.log"
    jarvis_log = logs_dir / "jarvis.log"

    # Flush handlers
    for handler in logging.getLogger().handlers + logging.getLogger("jarvis").handlers:
        handler.flush()

    app_content = app_log.read_text(encoding="utf-8")
    jarvis_content = jarvis_log.read_text(encoding="utf-8")

    assert test_message in app_content
    assert test_message in jarvis_content


def test_root_logger_writes_to_app_log(tmp_path: Path):
    logs_dir = tmp_path / "root_logs"
    setup_logging(logs_dir=logs_dir)

    root_message = "Third-party or root logging message"
    logging.getLogger("external_library").info(root_message)

    # Flush handlers
    for handler in logging.getLogger().handlers:
        handler.flush()

    app_content = (logs_dir / "app.log").read_text(encoding="utf-8")
    assert root_message in app_content
