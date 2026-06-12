"""MCP server — four tools for document-to-XML processing."""

import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from xml_processing_mcp.config import get_settings, setup_logging
from xml_processing_mcp.models import (
    ParseBatchRequest,
    ParseBatchResponse,
    ParseBatchResult,
    ParseDocumentRequest,
    ParseDocumentResponse,
    ParseFileRequest,
    SupportedTypesResponse,
)
from xml_processing_mcp.services.document_processing_service import DocumentProcessingService
from xml_processing_mcp.sinks.file_sink import FileSink
from xml_processing_mcp.sources.bytes_source import Base64Source
from xml_processing_mcp.sources.file_source import FileSource

_log = logging.getLogger(__name__)

mcp = FastMCP("document-xml-mcp")


@mcp.tool()
def list_supported_document_types() -> dict:
    """Return currently supported and planned document types."""
    _log.info("tool=list_supported_document_types")
    result = SupportedTypesResponse(supported=["docx"], planned=["pdf", "html", "markdown", "odt"]).model_dump()
    _log.debug("list_supported_document_types → %s", result)
    return result


@mcp.tool()
def parse_document_to_xml(filename: str, content_base64: str, document_type: str = "docx", profile: str = "generic") -> dict:
    """Parse a base64-encoded document and return simplified XML."""
    _log.info("tool=parse_document_to_xml filename=%r document_type=%r profile=%r base64_len=%d",
              filename, document_type, profile, len(content_base64))
    req = ParseDocumentRequest(filename=filename, content_base64=content_base64, document_type=document_type, profile=profile)
    try:
        source = Base64Source(req.content_base64)
        svc = DocumentProcessingService(get_settings())
        resp = svc.process(source, req.filename)
        _log.info("parse_document_to_xml OK filename=%r stats=%s", filename, resp.stats)
        return resp.model_dump()
    except Exception as exc:
        _log.warning("parse_document_to_xml FAILED filename=%r error=%s", filename, exc, exc_info=True)
        return ParseDocumentResponse(
            xml="",
            warnings=[str(exc)],
            stats={"source_type": document_type, "paragraph_count": 0, "table_count": 0, "character_count": 0},  # type: ignore[arg-type]
        ).model_dump()


@mcp.tool()
def parse_file_to_xml(path: str, document_type: str = "docx", profile: str = "generic") -> dict:
    """Parse a document from a local file path and return simplified XML.

    NOTE: 'path' must be a path on the SERVER's filesystem, not the client's.
    The server process working directory is the directory where it was launched.
    Allowed input directories are configured via XML_PROCESSING_ALLOWED_INPUT_DIRS.
    """
    cfg = get_settings()
    resolved = Path(path).resolve()
    _log.info("tool=parse_file_to_xml path=%r resolved=%s document_type=%r allowed_input_dirs=%s",
              path, resolved, document_type, cfg.allowed_input_dirs)
    req = ParseFileRequest(path=path, document_type=document_type, profile=profile)
    try:
        source = FileSource(req.path, cfg.allowed_input_dirs)
        svc = DocumentProcessingService(cfg)
        resp = svc.process(source, Path(req.path).name)
        _log.info("parse_file_to_xml OK path=%r stats=%s", path, resp.stats)
        return resp.model_dump()
    except Exception as exc:
        _log.warning("parse_file_to_xml FAILED path=%r resolved=%s error=%s", path, resolved, exc, exc_info=True)
        return ParseDocumentResponse(
            xml="",
            warnings=[str(exc)],
            stats={"source_type": document_type, "paragraph_count": 0, "table_count": 0, "character_count": 0},  # type: ignore[arg-type]
        ).model_dump()


@mcp.tool()
def parse_batch_to_xml(
    input_dir: str,
    output_dir: str,
    document_type: str = "docx",
    continue_on_error: bool = True,
) -> dict:
    """Parse all documents in input_dir and write XML files to output_dir.

    NOTE: Both paths must be accessible on the SERVER's filesystem.
    """
    cfg = get_settings()
    input_resolved = Path(input_dir).resolve()
    _log.info("tool=parse_batch_to_xml input_dir=%r resolved=%s output_dir=%r allowed_input_dirs=%s",
              input_dir, input_resolved, output_dir, cfg.allowed_input_dirs)
    req = ParseBatchRequest(
        input_dir=input_dir, output_dir=output_dir, document_type=document_type, continue_on_error=continue_on_error
    )

    allowed = [Path(d).resolve() for d in cfg.allowed_input_dirs]
    if not any(input_resolved == a or input_resolved.is_relative_to(a) for a in allowed):
        _log.warning("parse_batch_to_xml REJECTED input_dir=%r not in allowed=%s", input_dir, cfg.allowed_input_dirs)
        return ParseBatchResponse(
            processed=0,
            failed=0,
            results=[
                ParseBatchResult(filename="", output_path=None, warnings=[], error=f"Input dir '{req.input_dir}' not allowed")
            ],
        ).model_dump()

    files = list(input_resolved.glob("*.docx"))
    _log.info("parse_batch_to_xml found %d .docx files in %s", len(files), input_resolved)
    results: list[ParseBatchResult] = []
    processed = 0
    failed = 0

    for file in files:
        _log.debug("parse_batch_to_xml processing file=%s", file)
        try:
            source = FileSource(str(file), cfg.allowed_input_dirs)
            sink = FileSink(req.output_dir, cfg.allowed_output_dirs)
            svc = DocumentProcessingService(cfg)
            resp = svc.process(source, file.name, sink=sink)
            out_path = str(Path(req.output_dir) / f"{file.stem}.xml")
            results.append(ParseBatchResult(filename=file.name, output_path=out_path, warnings=resp.warnings))
            processed += 1
            _log.debug("parse_batch_to_xml OK file=%s out=%s", file.name, out_path)
        except Exception as exc:
            _log.warning("parse_batch_to_xml FAILED file=%s error=%s", file.name, exc, exc_info=True)
            results.append(ParseBatchResult(filename=file.name, output_path=None, warnings=[], error=str(exc)))
            failed += 1
            if not req.continue_on_error:
                break

    _log.info("parse_batch_to_xml done processed=%d failed=%d", processed, failed)
    return ParseBatchResponse(processed=processed, failed=failed, results=results).model_dump()


def run() -> None:
    setup_logging()
    _log.info("Starting document-xml-mcp server")
    mcp.run()


if __name__ == "__main__":
    run()
