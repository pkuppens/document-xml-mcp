"""Tests for application configuration."""

from xml_processing_mcp.config import Settings


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
