"""Tests for the MCP server stub."""

import os
from unittest.mock import patch

import pytest

from xml_processing_mcp.server import _start_transport, list_supported_document_types


def test_list_supported_document_types():
    result = list_supported_document_types()
    assert result["supported"] == ["docx"]
    assert "pdf" in result["planned"]
    assert "html" in result["planned"]


@pytest.fixture(autouse=True)
def _clean_fastmcp_env(monkeypatch):
    """Remove FASTMCP_HOST / FASTMCP_PORT before each transport test so that
    ``os.environ.setdefault`` calls are not suppressed by leftover values."""
    monkeypatch.delenv("FASTMCP_HOST", raising=False)
    monkeypatch.delenv("FASTMCP_PORT", raising=False)
    monkeypatch.delenv("MCP_HOST", raising=False)
    monkeypatch.delenv("MCP_PORT", raising=False)


def test_stdio_transport():
    with patch("xml_processing_mcp.server.mcp") as mock_mcp:
        _start_transport("stdio")
        mock_mcp.run.assert_called_once_with(transport="stdio")


def test_unknown_transport_falls_back_to_stdio():
    with patch("xml_processing_mcp.server.mcp") as mock_mcp:
        _start_transport("unknown-transport")
        mock_mcp.run.assert_called_once_with(transport="stdio")


def test_sse_transport_sets_env_defaults(monkeypatch):
    with patch("xml_processing_mcp.server.mcp") as mock_mcp:
        _start_transport("sse")
        mock_mcp.run.assert_called_once_with(transport="sse")
        assert os.environ.get("FASTMCP_HOST") == "0.0.0.0"
        assert os.environ.get("FASTMCP_PORT") == "8000"


def test_sse_transport_respects_custom_host_port(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "127.0.0.1")
    monkeypatch.setenv("MCP_PORT", "9000")
    with patch("xml_processing_mcp.server.mcp") as mock_mcp:
        _start_transport("sse")
        mock_mcp.run.assert_called_once_with(transport="sse")
        assert os.environ.get("FASTMCP_HOST") == "127.0.0.1"
        assert os.environ.get("FASTMCP_PORT") == "9000"


def test_streamable_http_transport_sets_env_defaults(monkeypatch):
    with patch("xml_processing_mcp.server.mcp") as mock_mcp:
        _start_transport("streamable-http")
        mock_mcp.run.assert_called_once_with(transport="streamable-http")
        assert os.environ.get("FASTMCP_HOST") == "0.0.0.0"
        assert os.environ.get("FASTMCP_PORT") == "8000"


def test_streamable_http_transport_respects_custom_host_port(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "192.168.1.1")
    monkeypatch.setenv("MCP_PORT", "8080")
    with patch("xml_processing_mcp.server.mcp") as mock_mcp:
        _start_transport("streamable-http")
        mock_mcp.run.assert_called_once_with(transport="streamable-http")
        assert os.environ.get("FASTMCP_HOST") == "192.168.1.1"
        assert os.environ.get("FASTMCP_PORT") == "8080"
