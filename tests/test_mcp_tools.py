"""Tests for MCP tools wired in server.py."""

import base64
import io
import zipfile

import pytest

from xml_processing_mcp.server import (
    list_supported_document_types,
    parse_document_to_xml,
    parse_file_to_xml,
)

_DOCUMENT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Hello MCP.</w:t></w:r></w:p>
  </w:body>
</w:document>"""


def _make_docx_b64() -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", _DOCUMENT_XML)
        zf.writestr("[Content_Types].xml", b"<Types/>")
    return base64.b64encode(buf.getvalue()).decode()


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
