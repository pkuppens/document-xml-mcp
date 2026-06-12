"""Tests for XML sinks."""

import tempfile
from pathlib import Path

import pytest

from xml_processing_mcp.sinks.base import XmlSink
from xml_processing_mcp.sinks.file_sink import FileSink
from xml_processing_mcp.sinks.return_sink import ReturnSink


def test_return_sink_returns_xml():
    sink = ReturnSink()
    result = sink.write_xml("doc", "<root/>")
    assert result == "<root/>"
    assert sink.last_xml == "<root/>"


def test_return_sink_implements_protocol():
    assert isinstance(ReturnSink(), XmlSink)


def test_file_sink_writes_file():
    with tempfile.TemporaryDirectory() as tmp:
        sink = FileSink(tmp, [tmp])
        out = sink.write_xml("cv.docx", "<doc/>")
        assert Path(out).read_text() == "<doc/>"
        assert Path(out).name == "cv.xml"


def test_file_sink_rejects_disallowed_dir():
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(ValueError, match="not within any allowed directory"):
            FileSink("/tmp/evil", [tmp])
