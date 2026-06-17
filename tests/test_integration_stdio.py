"""Integration tests — stdio subprocess round-trip.

These tests start the actual MCP server as a subprocess and verify real tool
calls over the MCP protocol using the stdio transport.

Run with:
    uv run pytest -m integration -v

Skip (normal suite):
    uv run pytest -m "not integration" -v
"""

from __future__ import annotations

import base64
import io
import json
import zipfile

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SERVER_PARAMS = StdioServerParameters(
    command="uv",
    args=["run", "document-xml-mcp"],
    env={
        "XML_PROCESSING_ALLOWED_INPUT_DIRS": "",
        "XML_PROCESSING_ALLOWED_OUTPUT_DIRS": "",
        "XML_PROCESSING_LOG_LEVEL": "WARNING",
    },
)


def _parse_result(result) -> dict:
    """Extract and JSON-decode the first content block from a CallToolResult.

    If the tool returned an error the raw content is returned as-is so tests
    can inspect it.
    """
    if result.isError:
        # Return a dict that tests can inspect for error details
        return {"error": True, "content": result.content}
    return json.loads(result.content[0].text)


def _make_minimal_docx() -> bytes:
    """Return the bytes of a minimal, well-formed DOCX file.

    A DOCX is a ZIP archive containing at minimum:
    - [Content_Types].xml
    - word/document.xml
    - _rels/.rels
    - word/_rels/document.xml.rels
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml"'
            ' ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1"'
            ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
            ' Target="word/document.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "word/_rels/document.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            "</Relationships>",
        )
        zf.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"'
            ' xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body>"
            "<w:p><w:r><w:t>Hello Integration Test</w:t></w:r></w:p>"
            "<w:sectPr/>"
            "</w:body>"
            "</w:document>",
        )
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_stdio_list_supported_types():
    """Verify list_supported_document_types returns docx as the supported type."""
    async with stdio_client(_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("list_supported_document_types", {})
            data = _parse_result(result)

    assert data["supported"] == ["docx"], f"Expected ['docx'], got {data['supported']!r}"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_stdio_parse_document_to_xml_valid():
    """Verify parse_document_to_xml returns XML for a minimal synthetic DOCX."""
    docx_bytes = _make_minimal_docx()
    content_b64 = base64.b64encode(docx_bytes).decode()

    async with stdio_client(_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "parse_document_to_xml",
                {"filename": "test.docx", "content_base64": content_b64},
            )
            data = _parse_result(result)

    assert "xml" in data, f"Response missing 'xml' key: {data}"
    assert data["xml"], "xml field is empty"
    assert "<document" in data["xml"], f"Expected '<document' in xml, got: {data['xml'][:300]}"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_stdio_parse_file_disallowed_path():
    """Verify parse_file_to_xml rejects a disallowed path (/etc/passwd)."""
    async with stdio_client(_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "parse_file_to_xml",
                {"path": "/etc/passwd"},
            )
            # Either the tool returns isError=True, or the result dict contains
            # an "error" key indicating rejection.
            if result.isError:
                # MCP-level error — path was rejected at the tool boundary
                return
            data = json.loads(result.content[0].text)
            assert "error" in data, f"Expected an error response for disallowed path '/etc/passwd', but got: {data}"
