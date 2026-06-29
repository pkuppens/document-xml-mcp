"""Tests for CV resources registered in server.py."""

import asyncio

from xml_processing_mcp.resources.cv_resources import get_assignment_format, get_cv_export_schema
from xml_processing_mcp.server import mcp

# --- unit tests: resource loader functions ---


def test_get_cv_export_schema_returns_xml():
    content = get_cv_export_schema()
    assert content.strip().startswith("<?xml") or content.strip().startswith("<document")
    assert "<document>" in content
    assert "<heading" in content
    assert "<section" in content


def test_get_assignment_format_returns_markdown():
    content = get_assignment_format()
    assert "# Assignment" in content or "## Title" in content
    assert "Required Skills" in content or "Required" in content


def test_get_cv_export_schema_is_non_empty():
    assert len(get_cv_export_schema()) > 200


def test_get_assignment_format_is_non_empty():
    assert len(get_assignment_format()) > 200


# --- MCP layer: verify resources are discoverable and readable ---


def test_mcp_lists_two_cv_resources():
    resources = asyncio.run(mcp.list_resources())
    uris = {str(r.uri) for r in resources}
    assert "cv://templates/export-schema" in uris
    assert "cv://templates/assignment-format" in uris


def test_mcp_read_export_schema_resource():
    contents = asyncio.run(mcp.read_resource("cv://templates/export-schema"))
    assert contents
    first = contents[0]
    text = first.content if hasattr(first, "content") else str(first)
    assert "<document>" in text


def test_mcp_read_assignment_format_resource():
    contents = asyncio.run(mcp.read_resource("cv://templates/assignment-format"))
    assert contents
    first = contents[0]
    text = first.content if hasattr(first, "content") else str(first)
    assert len(text) > 100


def test_mcp_resource_export_schema_has_mime_type():
    resources = asyncio.run(mcp.list_resources())
    schema = next((r for r in resources if str(r.uri) == "cv://templates/export-schema"), None)
    assert schema is not None
    assert schema.mimeType == "application/xml"


def test_mcp_resource_assignment_format_has_mime_type():
    resources = asyncio.run(mcp.list_resources())
    fmt = next((r for r in resources if str(r.uri) == "cv://templates/assignment-format"), None)
    assert fmt is not None
    assert fmt.mimeType == "text/markdown"
