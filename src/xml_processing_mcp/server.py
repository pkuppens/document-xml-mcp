"""MCP server — tools, prompts, and resources for document-to-XML processing and CV intelligence."""

import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from xml_processing_mcp.config import get_settings, setup_logging
from xml_processing_mcp.models import (
    ParseBatchRequest,
    ParseBatchResponse,
    ParseBatchResult,
    ParseDocumentRequest,
    ParseFileRequest,
    SupportedTypesResponse,
)
from xml_processing_mcp.prompts.cv_analysis import analyze_cv_gaps_prompt, answer_cv_questions_prompt
from xml_processing_mcp.prompts.cv_generation import rewrite_cv_for_assignment_prompt, write_motivation_letter_prompt
from xml_processing_mcp.resources.cv_resources import get_assignment_format, get_cv_export_schema
from xml_processing_mcp.services.cv_field_extractor import extract_cv_fields as _extract_cv_fields
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
    """Parse an uploaded document (provided as base64-encoded bytes) and return simplified XML.

    Use this tool when you have the FILE CONTENTS available as base64.
    If you want to parse a file that exists on the server's filesystem, use parse_file_to_xml instead.

    Parameters
    ----------
    filename:
        The file name including extension (e.g. "cv.docx").
        Used for extension validation and output naming only — NOT a file path.
        Do NOT put a full path here; put only the bare filename.
    content_base64:
        The file contents encoded as a base64 string.
        Must be the encoded BYTES of the document, not a file path.
        Generate with (PowerShell): [Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\\path\\to\\cv.docx"))
        Generate with (Bash/macOS): base64 -w 0 cv.docx   (Linux) / base64 -i cv.docx | tr -d '\\n'  (macOS)
    """
    _log.info("tool=parse_document_to_xml filename=%r document_type=%r base64_len=%d", filename, document_type, len(content_base64))
    req = ParseDocumentRequest(filename=filename, content_base64=content_base64, document_type=document_type, profile=profile)
    try:
        source = Base64Source(req.content_base64)
        svc = DocumentProcessingService(get_settings())
        resp = svc.process(source, req.filename)
        _log.info("parse_document_to_xml OK filename=%r stats=%s", filename, resp.stats)
        return resp.model_dump()
    except Exception as exc:
        _log.warning("parse_document_to_xml FAILED filename=%r: %s", filename, exc, exc_info=True)
        raise


@mcp.tool()
def parse_file_to_xml(path: str, document_type: str = "docx", profile: str = "generic") -> dict:
    """Parse a document from a file path on the SERVER's filesystem and return simplified XML.

    Use this tool when the file already exists on the machine running the MCP server.
    The path must be inside one of the configured allowed input directories
    (default: input/; override with XML_PROCESSING_ALLOWED_INPUT_DIRS).

    Recommended: copy your DOCX to the project's input/ directory and use a relative path.
    Example: copy cv.docx to input/CV_Test_1.docx, then call with path="input/CV_Test_1.docx".

    Parameters
    ----------
    path:
        Path to the document file. Relative paths are resolved from the server's working
        directory (the project root when launched with 'uv run document-xml-mcp').
        Example: input/CV_Test_1.docx
    """
    cfg = get_settings()
    resolved = Path(path).resolve()
    _log.info(
        "tool=parse_file_to_xml path=%r resolved=%s document_type=%r allowed_input_dirs=%s",
        path,
        resolved,
        document_type,
        cfg.allowed_input_dirs,
    )
    req = ParseFileRequest(path=path, document_type=document_type, profile=profile)
    try:
        source = FileSource(req.path, cfg.allowed_input_dirs)
        svc = DocumentProcessingService(cfg)
        resp = svc.process(source, Path(req.path).name)
        _log.info("parse_file_to_xml OK path=%r stats=%s", path, resp.stats)
        return resp.model_dump()
    except Exception as exc:
        _log.warning("parse_file_to_xml FAILED path=%r resolved=%s: %s", path, resolved, exc, exc_info=True)
        raise


@mcp.tool()
def parse_batch_to_xml(
    input_dir: str,
    output_dir: str,
    document_type: str = "docx",
    continue_on_error: bool = True,
) -> dict:
    """Parse all .docx files in input_dir and write XML files to output_dir.

    Both paths must be accessible on the SERVER's filesystem and inside the
    configured allowed directories (XML_PROCESSING_ALLOWED_INPUT/OUTPUT_DIRS).
    """
    cfg = get_settings()
    input_resolved = Path(input_dir).resolve()
    _log.info(
        "tool=parse_batch_to_xml input_dir=%r resolved=%s output_dir=%r allowed_input_dirs=%s",
        input_dir,
        input_resolved,
        output_dir,
        cfg.allowed_input_dirs,
    )
    req = ParseBatchRequest(
        input_dir=input_dir, output_dir=output_dir, document_type=document_type, continue_on_error=continue_on_error
    )

    allowed = [Path(d).resolve() for d in cfg.allowed_input_dirs]
    if not any(input_resolved == a or input_resolved.is_relative_to(a) for a in allowed):
        msg = f"Input dir '{req.input_dir}' is not within any allowed directory: {cfg.allowed_input_dirs}"
        _log.warning("parse_batch_to_xml REJECTED input_dir=%r: %s", input_dir, msg)
        raise ValueError(msg)

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
            _log.warning("parse_batch_to_xml FAILED file=%s: %s", file.name, exc, exc_info=True)
            results.append(ParseBatchResult(filename=file.name, output_path=None, warnings=[], error=str(exc)))
            failed += 1
            if not req.continue_on_error:
                break

    _log.info("parse_batch_to_xml done processed=%d failed=%d", processed, failed)
    return ParseBatchResponse(processed=processed, failed=failed, results=results).model_dump()


@mcp.tool()
def extract_cv_fields(xml: str) -> dict:
    """Extract structured fields from CV XML into a JSON object.

    Parses the clean XML produced by parse_document_to_xml and returns
    named fields: name, contact (email, phone, linkedin), summary, skills,
    experience, education, languages, certifications, and warnings.

    Use this after parse_document_to_xml to make the CV machine-readable
    for downstream matching, gap analysis, or storage.

    Parameters
    ----------
    xml:
        CV XML string as returned by parse_document_to_xml or parse_file_to_xml.
        Must be well-formed XML.
    """
    _log.info("tool=extract_cv_fields xml_len=%d", len(xml))
    try:
        result = _extract_cv_fields(xml)
        _log.info(
            "extract_cv_fields OK name=%r skills=%d experience=%d",
            result.get("name"),
            len(result.get("skills", [])),
            len(result.get("experience", [])),
        )
        return result
    except Exception as exc:
        _log.warning("extract_cv_fields FAILED: %s", exc, exc_info=True)
        raise


# --- CV Prompt Templates ---
# Prompts are reusable LLM instruction templates. The server returns the template;
# the MCP client sends it to the LLM. See docs/adr/ADR-002-mcp-prompt-ownership.md.


@mcp.prompt(
    description="Identify skill and experience gaps between a CV and a job description. "
    "Pass cv_xml from parse_document_to_xml and the job description as plain text.",
)
def analyze_cv_gaps(cv_xml: str, job_description: str) -> list[dict]:
    """Gap analysis: compare CV XML against a job description and list missing skills/experience."""
    return analyze_cv_gaps_prompt(cv_xml, job_description)


@mcp.prompt(
    description="Answer a specific question about a CV based strictly on its XML content. "
    "Suitable for: years of experience, companies worked for, highest degree, etc.",
)
def answer_cv_questions(cv_xml: str, question: str) -> list[dict]:
    """Q&A over CV XML: answer a question based only on the CV content."""
    return answer_cv_questions_prompt(cv_xml, question)


@mcp.prompt(
    description="Write a tailored motivation letter for a specific assignment. "
    "tone options: 'professional' (default), 'enthusiastic', 'concise'.",
)
def write_motivation_letter(cv_xml: str, assignment: str, tone: str = "professional") -> list[dict]:
    """Generate a motivation letter tailored to an assignment, drawing on CV XML content."""
    return write_motivation_letter_prompt(cv_xml, assignment, tone)


@mcp.prompt(
    description="Rewrite and tailor a CV for a specific assignment. "
    "Reorders and rephrases existing content — does not fabricate experience. "
    "target_format: 'xml' (default) or 'markdown'.",
)
def rewrite_cv_for_assignment(cv_xml: str, assignment: str, target_format: str = "xml") -> list[dict]:
    """Tailor CV XML for a specific assignment by emphasising the most relevant experience."""
    return rewrite_cv_for_assignment_prompt(cv_xml, assignment, target_format)


# --- CV Resources ---
# Resources are static reference data the LLM reads as context.
# See docs/adr/ADR-003-mcp-resource-vs-prompt.md.


@mcp.resource(
    "cv://templates/export-schema",
    name="CV Export Schema",
    description="XML structure produced by parse_document_to_xml for CV/resume documents. "
    "Use as reference when generating or validating CV XML output.",
    mime_type="application/xml",
)
def cv_export_schema() -> str:
    """Return the annotated CV XML schema."""
    return get_cv_export_schema()


@mcp.resource(
    "cv://templates/assignment-format",
    name="Assignment Description Format",
    description="Expected structure of a job description / assignment used with analyze_cv_gaps "
    "and write_motivation_letter prompts. Includes required and optional fields.",
    mime_type="text/markdown",
)
def assignment_format() -> str:
    """Return the assignment description format template."""
    return get_assignment_format()


def _start_transport(transport: str) -> None:
    """Dispatch to the appropriate MCP transport.

    Separated from ``run()`` so that unit tests can call this function directly
    with ``mcp.run`` patched, without starting an actual event loop.
    """
    if transport == "sse":
        # FastMCP reads FASTMCP_HOST / FASTMCP_PORT from the environment.
        # Map our MCP_HOST / MCP_PORT vars so callers only need one set of names.
        os.environ.setdefault("FASTMCP_HOST", os.environ.get("MCP_HOST", "0.0.0.0"))
        os.environ.setdefault("FASTMCP_PORT", os.environ.get("MCP_PORT", "8000"))
        mcp.run(transport="sse")
    elif transport == "streamable-http":
        os.environ.setdefault("FASTMCP_HOST", os.environ.get("MCP_HOST", "0.0.0.0"))
        os.environ.setdefault("FASTMCP_PORT", os.environ.get("MCP_PORT", "8000"))
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


def run() -> None:  # pragma: no cover — MCP server entrypoint; starts an infinite event loop
    setup_logging()
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    _log.info("Starting document-xml-mcp server transport=%s", transport)
    _start_transport(transport)


if __name__ == "__main__":  # pragma: no cover
    run()
