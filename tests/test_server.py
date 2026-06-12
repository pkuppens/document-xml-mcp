"""Tests for the MCP server stub."""

from xml_processing_mcp.server import list_supported_document_types


def test_list_supported_document_types():
    result = list_supported_document_types()
    assert result["supported"] == ["docx"]
    assert "pdf" in result["planned"]
    assert "html" in result["planned"]
