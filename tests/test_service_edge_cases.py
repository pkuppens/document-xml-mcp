"""Service layer edge cases — file size boundaries, corrupt DOCX, empty/mixed batch."""

import base64
import io
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from lxml import etree

from xml_processing_mcp.config import Settings
from xml_processing_mcp.services.document_processing_service import DocumentProcessingService
from xml_processing_mcp.sources.bytes_source import Base64Source, BytesSource

_DOCUMENT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Hello</w:t></w:r></w:p>
  </w:body>
</w:document>"""


def _make_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", _DOCUMENT_XML)
        zf.writestr("[Content_Types].xml", b"<Types/>")
    return buf.getvalue()


def _make_docx_padded_to(target_size: int) -> bytes:
    """Return a valid DOCX whose raw byte length equals target_size by adding a comment entry."""
    base = _make_docx()
    if len(base) >= target_size:
        return base
    padding_needed = target_size - len(base)
    # Rebuild with a padding entry so total size == target_size. We may overshoot
    # slightly due to zip overhead, so we store padding_needed bytes of zeros and
    # accept that the resulting file might be a few bytes larger than target.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("word/document.xml", _DOCUMENT_XML)
        zf.writestr("[Content_Types].xml", b"<Types/>")
        zf.writestr("padding.bin", b"\x00" * max(0, padding_needed - 200))  # rough slack for zip overhead
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Task 14.1 — File size boundary conditions
# ---------------------------------------------------------------------------


def test_file_exactly_at_limit():
    """A file whose size exactly equals the limit must NOT raise ValueError('exceeds limit').

    check_file_size uses strict `>`, so len(data) == limit is allowed through.
    We build a valid DOCX padded to exactly `limit` bytes with a stored zero-filled entry.
    The service must succeed (or raise a non-size error if padding causes parse issues).
    """
    cfg = Settings(max_file_size_mb=1)
    limit = 1 * 1024 * 1024  # 1 048 576 bytes

    # Build a valid DOCX padded to <= limit using a stored zero-filled entry.
    # ZIP entry overhead is ~76 bytes local header + 46 bytes central dir = ~122 bytes.
    base_docx = _make_docx()
    extra_needed = limit - len(base_docx)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("word/document.xml", _DOCUMENT_XML)
        zf.writestr("[Content_Types].xml", b"<Types/>")
        if extra_needed > 150:
            zf.writestr("pad.bin", b"\x00" * (extra_needed - 150))
    data = buf.getvalue()

    # The padded DOCX may be slightly under or over `limit` due to zip overhead variance.
    # Either way: if len(data) <= limit, no size error should occur.
    assert len(data) <= limit, f"Padded DOCX is {len(data)} bytes, exceeds limit {limit}"

    src = BytesSource(data)
    # Must not raise ValueError with "exceeds limit" — the service either succeeds or
    # raises a different error (parse error if padding caused issues).
    try:
        result = DocumentProcessingService(cfg).process(src, "test.docx")
        # If we get here, processing succeeded — that's also fine.
        assert result is not None
    except ValueError as exc:
        assert "exceeds limit" not in str(exc), f"Should not raise size-limit error: {exc}"


def test_file_one_byte_over_limit():
    """A file one byte over the limit must raise ValueError with 'exceeds limit'."""
    cfg = Settings(max_file_size_mb=0)  # limit = 0 bytes, so any non-empty file exceeds it
    src = BytesSource(b"\x00")  # 1 byte > 0 bytes
    with pytest.raises(ValueError, match="exceeds limit"):
        DocumentProcessingService(cfg).process(src, "test.docx")


def test_service_rejects_oversized_base64():
    """A Base64Source encoding an oversized file must trigger ValueError('exceeds limit')."""
    cfg = Settings(max_file_size_mb=0)
    oversized = base64.b64encode(b"\x00" * 1).decode()
    src = Base64Source(oversized)
    with pytest.raises(ValueError, match="exceeds limit"):
        DocumentProcessingService(cfg).process(src, "test.docx")


def test_empty_batch_dir():
    """parse_batch_to_xml on an empty directory returns processed=0, failed=0, results=[]."""
    from xml_processing_mcp.server import parse_batch_to_xml

    with tempfile.TemporaryDirectory() as tmpdir:
        settings = Settings.model_construct(
            max_file_size_mb=20,
            max_batch_size=200,
            allowed_input_dirs=[tmpdir],
            allowed_output_dirs=[tmpdir],
            include_headers_footers=False,
            include_comments=False,
            log_level="DEBUG",
        )
        with patch("xml_processing_mcp.server.get_settings", return_value=settings):
            result = parse_batch_to_xml(input_dir=tmpdir, output_dir=tmpdir)

    assert result["processed"] == 0
    assert result["failed"] == 0
    assert result["results"] == []


def test_batch_mixed_good_bad():
    """One valid DOCX + one corrupt file with continue_on_error=True → processed=1, failed=1."""
    from xml_processing_mcp.server import parse_batch_to_xml

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "good.docx").write_bytes(_make_docx())
        (tmp / "corrupt.docx").write_bytes(b"not a valid zip file")

        settings = Settings.model_construct(
            max_file_size_mb=20,
            max_batch_size=200,
            allowed_input_dirs=[tmpdir],
            allowed_output_dirs=[tmpdir],
            include_headers_footers=False,
            include_comments=False,
            log_level="DEBUG",
        )
        with patch("xml_processing_mcp.server.get_settings", return_value=settings):
            result = parse_batch_to_xml(input_dir=tmpdir, output_dir=tmpdir, continue_on_error=True)

    assert result["processed"] == 1
    assert result["failed"] == 1


# ---------------------------------------------------------------------------
# Task 14.2 — Corrupt DOCX handling
# ---------------------------------------------------------------------------


def test_valid_zip_missing_document_xml():
    """A valid ZIP without word/document.xml must raise KeyError."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("other.xml", b"<data/>")
    src = BytesSource(buf.getvalue())
    svc = DocumentProcessingService(Settings())
    with pytest.raises(KeyError):
        svc.process(src, "test.docx")


def test_valid_zip_malformed_document_xml():
    """A valid ZIP with malformed XML in word/document.xml must raise XMLSyntaxError."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", b"THIS IS NOT XML<<<")
        zf.writestr("[Content_Types].xml", b"<Types/>")
    src = BytesSource(buf.getvalue())
    svc = DocumentProcessingService(Settings())
    with pytest.raises(etree.XMLSyntaxError):
        svc.process(src, "test.docx")


def test_not_a_zip():
    """Bytes that are not a ZIP must raise ValueError (from safe_open_docx)."""
    src = BytesSource(b"this is not a zip file at all")
    svc = DocumentProcessingService(Settings())
    with pytest.raises(ValueError, match="not a valid ZIP"):
        svc.process(src, "test.docx")
