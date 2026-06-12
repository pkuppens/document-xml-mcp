"""Tests for DocumentProcessingService."""

import io
import zipfile

from lxml import etree

from xml_processing_mcp.config import Settings
from xml_processing_mcp.services.document_processing_service import DocumentProcessingService
from xml_processing_mcp.sinks.return_sink import ReturnSink
from xml_processing_mcp.sources.bytes_source import BytesSource

_DOCUMENT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:r><w:t>Hello</w:t></w:r>
    </w:p>
    <w:p><w:r><w:t>World paragraph.</w:t></w:r></w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Cell</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
  </w:body>
</w:document>"""


def _make_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", _DOCUMENT_XML)
        zf.writestr("[Content_Types].xml", b"<Types/>")
    return buf.getvalue()


def _service() -> DocumentProcessingService:
    return DocumentProcessingService(Settings())


def test_process_returns_non_empty_xml():
    src = BytesSource(_make_docx())
    resp = _service().process(src, "cv.docx")
    assert resp.xml.strip()
    etree.fromstring(resp.xml.encode())  # must be valid XML


def test_process_stats_paragraph_count():
    src = BytesSource(_make_docx())
    resp = _service().process(src, "cv.docx")
    assert resp.stats.paragraph_count >= 0


def test_process_stats_table_count():
    src = BytesSource(_make_docx())
    resp = _service().process(src, "cv.docx")
    assert resp.stats.table_count == 1


def test_process_uses_custom_sink():
    sink = ReturnSink()
    src = BytesSource(_make_docx())
    resp = _service().process(src, "cv.docx", sink=sink)
    assert sink.last_xml == resp.xml


def test_process_rejects_oversized_file():
    import pytest

    from xml_processing_mcp.config import Settings

    cfg = Settings(max_file_size_mb=0)
    svc = DocumentProcessingService(cfg)
    src = BytesSource(_make_docx())
    with pytest.raises(ValueError, match="exceeds limit"):
        svc.process(src, "cv.docx")
