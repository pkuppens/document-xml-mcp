"""Tests for security helpers."""

import io
import zipfile

import pytest

from xml_processing_mcp.security.file_limits import check_extension, check_file_size
from xml_processing_mcp.security.zip_safety import safe_open_docx

# --- file_limits ---


def test_check_file_size_passes():
    check_file_size(b"x" * 100, max_mb=1)  # should not raise


def test_check_file_size_rejects_oversized():
    with pytest.raises(ValueError, match="exceeds limit"):
        check_file_size(b"x" * (2 * 1024 * 1024 + 1), max_mb=2)


def test_check_extension_passes_docx():
    check_extension("cv.docx")


def test_check_extension_rejects_docm():
    with pytest.raises(ValueError, match=".docm"):
        check_extension("malicious.docm")


def test_check_extension_rejects_unknown():
    with pytest.raises(ValueError, match="Unsupported"):
        check_extension("file.pdf")


# --- zip_safety ---


def _make_zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_safe_open_docx_valid():
    data = _make_zip({"word/document.xml": b"<root/>"})
    zf = safe_open_docx(data)
    assert "word/document.xml" in zf.namelist()
    zf.close()


def test_safe_open_docx_rejects_non_zip():
    with pytest.raises(ValueError, match="valid ZIP"):
        safe_open_docx(b"not a zip at all")


def test_safe_open_docx_rejects_path_traversal():
    data = _make_zip({"../evil.xml": b"bad"})
    with pytest.raises(ValueError, match="path traversal"):
        safe_open_docx(data)


def test_safe_open_docx_rejects_zip_bomb():
    # Write 201 MB of null bytes with DEFLATE — compressed size is tiny, uncompressed is real.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("big.xml", b"\x00" * (201 * 1024 * 1024))
    with pytest.raises(ValueError, match="ZIP bomb"):
        safe_open_docx(buf.getvalue())
