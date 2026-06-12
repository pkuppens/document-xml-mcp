"""Tests for document sources."""

import base64
import tempfile
from pathlib import Path

import pytest

from xml_processing_mcp.sources.base import DocumentSource
from xml_processing_mcp.sources.bytes_source import Base64Source, BytesSource
from xml_processing_mcp.sources.file_source import FileSource


def test_bytes_source_returns_data():
    data = b"hello bytes"
    assert BytesSource(data).get_document_bytes() == data


def test_bytes_source_implements_protocol():
    assert isinstance(BytesSource(b""), DocumentSource)


def test_base64_source_decodes():
    data = b"hello base64"
    encoded = base64.b64encode(data).decode()
    assert Base64Source(encoded).get_document_bytes() == data


def test_base64_source_empty_string_is_not_a_path():
    """Empty string (after stripping) must not be flagged as a path — it should fail at decode."""
    from xml_processing_mcp.sources.bytes_source import _looks_like_path

    assert _looks_like_path("") is False
    assert _looks_like_path('""') is False


def test_base64_source_rejects_windows_path():
    with pytest.raises(ValueError, match="parse_file_to_xml"):
        Base64Source(r"C:\Users\piete\Downloads\cv.docx").get_document_bytes()


def test_base64_source_rejects_quoted_windows_path():
    with pytest.raises(ValueError, match="parse_file_to_xml"):
        Base64Source('"C:\\Users\\piete\\Downloads\\cv.docx"').get_document_bytes()


def test_base64_source_rejects_unix_path():
    with pytest.raises(ValueError, match="parse_file_to_xml"):
        Base64Source("/home/user/cv.docx").get_document_bytes()


def test_base64_source_rejects_unc_path():
    with pytest.raises(ValueError, match="parse_file_to_xml"):
        Base64Source("\\\\server\\share\\cv.docx").get_document_bytes()


def test_file_source_reads_file():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "doc.docx"
        p.write_bytes(b"file content")
        src = FileSource(str(p), [tmp])
        assert src.get_document_bytes() == b"file content"


def test_file_source_rejects_outside_dir():
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(ValueError, match="not within any allowed directory"):
            FileSource("/etc/passwd", [tmp])


def test_file_source_rejects_path_traversal():
    with tempfile.TemporaryDirectory() as tmp:
        traversal = str(Path(tmp) / ".." / ".." / "etc" / "passwd")
        with pytest.raises(ValueError, match="not within any allowed directory"):
            FileSource(traversal, [tmp])
