"""Tests for MCP tools wired in server.py."""

import base64
import io
import zipfile

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


def test_list_supported_document_types():
    result = list_supported_document_types()
    assert result["supported"] == ["docx"]
    assert "pdf" in result["planned"]


def test_parse_document_to_xml_valid():
    result = parse_document_to_xml(filename="test.docx", content_base64=_make_docx_b64())
    assert result["xml"]
    assert "<" in result["xml"]
    assert result["warnings"] == []


def test_parse_document_to_xml_invalid_base64():
    result = parse_document_to_xml(filename="test.docx", content_base64="!!notbase64!!")
    # Should return error in warnings, not raise
    assert result["warnings"]


def test_parse_file_to_xml_disallowed_path(monkeypatch):
    # Default allowed_input_dirs = ["/input"]; /etc/passwd is outside
    result = parse_file_to_xml(path="/etc/passwd")
    assert result["warnings"]
    assert result["xml"] == ""


def test_parse_document_to_xml_unsupported_extension():
    result = parse_document_to_xml(filename="file.pdf", content_base64=_make_docx_b64())
    assert result["warnings"]
