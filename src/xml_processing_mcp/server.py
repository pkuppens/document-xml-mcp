"""MCP server — four tools for document-to-XML processing."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from xml_processing_mcp.config import get_settings
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

mcp = FastMCP("document-xml-mcp")


@mcp.tool()
def list_supported_document_types() -> dict:
    """Return currently supported and planned document types."""
    return SupportedTypesResponse(supported=["docx"], planned=["pdf", "html", "markdown", "odt"]).model_dump()


@mcp.tool()
def parse_document_to_xml(filename: str, content_base64: str, document_type: str = "docx", profile: str = "generic") -> dict:
    """Parse a base64-encoded document and return simplified XML."""
    req = ParseDocumentRequest(filename=filename, content_base64=content_base64, document_type=document_type, profile=profile)
    try:
        source = Base64Source(req.content_base64)
        svc = DocumentProcessingService(get_settings())
        resp = svc.process(source, req.filename)
        return resp.model_dump()
    except Exception as exc:
        return ParseDocumentResponse(
            xml="",
            warnings=[str(exc)],
            stats={"source_type": document_type, "paragraph_count": 0, "table_count": 0, "character_count": 0},  # type: ignore[arg-type]
        ).model_dump()


@mcp.tool()
def parse_file_to_xml(path: str, document_type: str = "docx", profile: str = "generic") -> dict:
    """Parse a document from a local file path and return simplified XML."""
    req = ParseFileRequest(path=path, document_type=document_type, profile=profile)
    cfg = get_settings()
    try:
        source = FileSource(req.path, cfg.allowed_input_dirs)
        svc = DocumentProcessingService(cfg)
        resp = svc.process(source, Path(req.path).name)
        return resp.model_dump()
    except Exception as exc:
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
    """Parse all documents in input_dir and write XML files to output_dir."""
    req = ParseBatchRequest(
        input_dir=input_dir, output_dir=output_dir, document_type=document_type, continue_on_error=continue_on_error
    )
    cfg = get_settings()

    # Validate input_dir is allowed
    input_path = Path(req.input_dir).resolve()
    allowed = [Path(d).resolve() for d in cfg.allowed_input_dirs]
    if not any(input_path == a or input_path.is_relative_to(a) for a in allowed):
        return ParseBatchResponse(
            processed=0,
            failed=0,
            results=[
                ParseBatchResult(filename="", output_path=None, warnings=[], error=f"Input dir '{req.input_dir}' not allowed")
            ],
        ).model_dump()

    files = list(input_path.glob("*.docx"))
    results: list[ParseBatchResult] = []
    processed = 0
    failed = 0

    for file in files:
        try:
            source = FileSource(str(file), cfg.allowed_input_dirs)
            sink = FileSink(req.output_dir, cfg.allowed_output_dirs)
            svc = DocumentProcessingService(cfg)
            resp = svc.process(source, file.name, sink=sink)
            out_path = str(Path(req.output_dir) / f"{file.stem}.xml")
            results.append(ParseBatchResult(filename=file.name, output_path=out_path, warnings=resp.warnings))
            processed += 1
        except Exception as exc:
            results.append(ParseBatchResult(filename=file.name, output_path=None, warnings=[], error=str(exc)))
            failed += 1
            if not req.continue_on_error:
                break

    return ParseBatchResponse(processed=processed, failed=failed, results=results).model_dump()


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
