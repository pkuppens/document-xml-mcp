"""Tests for application configuration."""

import logging

from xml_processing_mcp.config import Settings, setup_logging


def test_defaults():
    s = Settings()
    assert s.max_file_size_mb == 20
    assert s.max_batch_size == 200
    assert s.allowed_input_dirs == ["/input"]
    assert s.allowed_output_dirs == ["/output"]
    assert s.include_headers_footers is False
    assert s.include_comments is False
    assert s.log_level == "DEBUG"


def test_env_override(monkeypatch):
    monkeypatch.setenv("XML_PROCESSING_MAX_FILE_SIZE_MB", "50")
    monkeypatch.setenv("XML_PROCESSING_LOG_LEVEL", "DEBUG")
    s = Settings()
    assert s.max_file_size_mb == 50
    assert s.log_level == "DEBUG"


def test_setup_logging_configures_root_logger():
    root = logging.getLogger()
    # Remove existing handlers so basicConfig can reconfigure the level.
    original_handlers = root.handlers[:]
    root.handlers.clear()
    try:
        setup_logging(Settings.model_construct(log_level="WARNING"))
        assert root.level == logging.WARNING
    finally:
        root.handlers = original_handlers


def test_setup_logging_no_args_uses_get_settings():
    """setup_logging() with no argument must not raise."""
    setup_logging()  # covers the `if settings is None: settings = get_settings()` branch
