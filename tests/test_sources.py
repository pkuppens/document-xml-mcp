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
