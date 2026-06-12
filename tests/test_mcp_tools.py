"""Tests for MCP tools wired in server.py."""

import base64
import io
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from xml_processing_mcp.config import Settings
from xml_processing_mcp.server import (
    list_supported_document_types,
    parse_batch_to_xml,
    parse_document_to_xml,
    parse_file_to_xml,
)

_DOCUMENT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Hello MCP.</w:t></w:r></w:p>
  </w:body>
</w:document>"""


def _make_docx_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", _DOCUMENT_XML)
        zf.writestr("[Content_Types].xml", b"<Types/>")
    return buf.getvalue()


def _make_docx_b64() -> str:
    return base64.b64encode(_make_docx_bytes()).decode()


def _settings_for(tmp_path: Path) -> Settings:
    return Settings.model_construct(
        max_file_size_mb=20,
        max_batch_size=200,
        allowed_input_dirs=[str(tmp_path)],
        allowed_output_dirs=[str(tmp_path)],
        include_headers_footers=False,
        include_comments=False,
        log_level="DEBUG",
    )


# --- success cases ---


def test_list_supported_document_types():
    result = list_supported_document_types()
    assert result["supported"] == ["docx"]
    assert "pdf" in result["planned"]


def test_parse_document_to_xml_valid():
    result = parse_document_to_xml(filename="test.docx", content_base64=_make_docx_b64())
    assert result["xml"]
    assert "<" in result["xml"]
    assert result["warnings"] == []


# --- error cases: tools must RAISE, not return silent empty-xml dicts ---


def test_parse_document_to_xml_invalid_base64_raises():
    with pytest.raises(Exception):
        parse_document_to_xml(filename="test.docx", content_base64="!!notbase64!!")


def test_parse_document_to_xml_windows_path_in_base64_raises():
    """Providing a file path in content_base64 must raise with a helpful message."""
    with pytest.raises(ValueError, match="parse_file_to_xml"):
        parse_document_to_xml(
            filename="cv.docx",
            content_base64=r"C:\Users\piete\Downloads\CV_Pieter_Kuppens.docx",
        )


def test_parse_document_to_xml_quoted_windows_path_in_base64_raises():
    with pytest.raises(ValueError, match="parse_file_to_xml"):
        parse_document_to_xml(
            filename="cv.docx",
            content_base64='"C:\\Users\\piete\\Downloads\\CV_Pieter_Kuppens.docx"',
        )


def test_parse_document_to_xml_unix_path_in_base64_raises():
    with pytest.raises(ValueError, match="parse_file_to_xml"):
        parse_document_to_xml(filename="cv.docx", content_base64="/home/user/cv.docx")


def test_parse_file_to_xml_disallowed_path_raises():
    with pytest.raises(ValueError, match="not within any allowed directory"):
        parse_file_to_xml(path="/etc/passwd")


def test_parse_document_to_xml_unsupported_extension_raises():
    with pytest.raises(ValueError, match="Unsupported"):
        parse_document_to_xml(filename="file.pdf", content_base64=_make_docx_b64())


def test_parse_file_to_xml_success(tmp_path):
    docx = tmp_path / "doc.docx"
    docx.write_bytes(_make_docx_bytes())
    with patch("xml_processing_mcp.server.get_settings", return_value=_settings_for(tmp_path)):
        result = parse_file_to_xml(path=str(docx))
    assert result["xml"]
    assert result["warnings"] == []


def test_parse_batch_to_xml_success(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    (input_dir / "a.docx").write_bytes(_make_docx_bytes())
    (input_dir / "b.docx").write_bytes(_make_docx_bytes())
    settings = Settings.model_construct(
        max_file_size_mb=20,
        max_batch_size=200,
        allowed_input_dirs=[str(input_dir)],
        allowed_output_dirs=[str(output_dir)],
        include_headers_footers=False,
        include_comments=False,
        log_level="DEBUG",
    )
    with patch("xml_processing_mcp.server.get_settings", return_value=settings):
        result = parse_batch_to_xml(input_dir=str(input_dir), output_dir=str(output_dir))
    assert result["processed"] == 2
    assert result["failed"] == 0


def test_parse_batch_to_xml_disallowed_input_raises(tmp_path):
    with patch("xml_processing_mcp.server.get_settings", return_value=_settings_for(tmp_path)):
        with pytest.raises(ValueError, match="not within any allowed directory"):
            parse_batch_to_xml(input_dir="/etc", output_dir=str(tmp_path))


def test_parse_batch_to_xml_continue_on_error_false_stops_on_first_failure(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    (input_dir / "bad.docx").write_bytes(b"not a zip")
    settings = Settings.model_construct(
        max_file_size_mb=20,
        max_batch_size=200,
        allowed_input_dirs=[str(input_dir)],
        allowed_output_dirs=[str(output_dir)],
        include_headers_footers=False,
        include_comments=False,
        log_level="DEBUG",
    )
    with patch("xml_processing_mcp.server.get_settings", return_value=settings):
        result = parse_batch_to_xml(input_dir=str(input_dir), output_dir=str(output_dir), continue_on_error=False)
    assert result["failed"] == 1
    assert result["results"][0]["error"] is not None
