"""Tests for Pydantic request and response models."""

from xml_processing_mcp.models import (
    ParseBatchRequest,
    ParseBatchResponse,
    ParseBatchResult,
    ParseDocumentRequest,
    ParseDocumentResponse,
    ParseFileRequest,
    ParseStats,
    SupportedTypesResponse,
)


def test_parse_document_request_defaults():
    r = ParseDocumentRequest(filename="cv.docx", content_base64="abc=")
    assert r.document_type == "docx"
    assert r.profile == "generic"


def test_parse_file_request_defaults():
    r = ParseFileRequest(path="/input/cv.docx")
    assert r.document_type == "docx"


def test_parse_batch_request_defaults():
    r = ParseBatchRequest(input_dir="/input", output_dir="/output")
    assert r.continue_on_error is True


def test_parse_document_response_serialisation():
    stats = ParseStats(source_type="docx", paragraph_count=5, table_count=1, character_count=200)
    resp = ParseDocumentResponse(xml="<doc/>", warnings=[], stats=stats)
    d = resp.model_dump()
    assert d["xml"] == "<doc/>"
    assert d["stats"]["paragraph_count"] == 5


def test_parse_batch_response():
    result = ParseBatchResult(filename="cv.docx", output_path="/output/cv.xml", warnings=[])
    resp = ParseBatchResponse(processed=1, failed=0, results=[result])
    assert resp.processed == 1
    assert resp.results[0].error is None


def test_supported_types_response():
    r = SupportedTypesResponse(supported=["docx"], planned=["pdf"])
    assert "docx" in r.supported
    assert "pdf" in r.planned
