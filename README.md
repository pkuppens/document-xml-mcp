# document-xml-mcp

An MCP server that accepts document files (currently DOCX) and returns simplified, semantic XML — stripping all formatting noise while preserving the document's structural content: headings, paragraphs, lists, tables, and links.

**Current scope:** DOCX is fully supported. PDF support is planned but not yet implemented.

---

## Quickstart

```bash
# Install dependencies
uv sync

# Run the MCP server (stdio transport)
uv run document-xml-mcp
```

---

## Run with Docker

```bash
# Build and run
docker compose up

# Place .docx files in ./input, XML output appears in ./output
```

The container reads from `/input` (read-only) and writes to `/output`.

---

## MCP Tool Reference

| Tool | Description | Key Inputs | Output |
|------|-------------|------------|--------|
| `list_supported_document_types` | Returns supported and planned document types | — | `{supported, planned}` |
| `parse_document_to_xml` | Parse a base64-encoded document to XML | `filename`, `content_base64` | `{xml, warnings, stats}` |
| `parse_file_to_xml` | Parse a document from a local file path | `path` | `{xml, warnings, stats}` |
| `parse_batch_to_xml` | Parse all `.docx` files in a directory | `input_dir`, `output_dir` | `{processed, failed, results}` |

---

## Example XML Output

Input: a DOCX CV for Jane Doe.

```xml
<document>
  <body>
    <heading level="1" class="Title">Jane Doe</heading>
    <section class="Heading1" title="Profile">
      <paragraph>Senior software developer with data and AI experience.</paragraph>
    </section>
    <section class="Heading1" title="Experience">
      <list>
        <item>Python</item>
        <item>C#/.NET</item>
        <item>SQL</item>
      </list>
      <table>
        <row>
          <cell>Year</cell>
          <cell>Role</cell>
        </row>
        <row>
          <cell>2020</cell>
          <cell>Data Engineer</cell>
        </row>
      </table>
    </section>
  </body>
</document>
```

The renderer removes empty nodes, strips useless attributes, and promotes redundant single-child wrapper nodes.

---

## Configuration

All settings use the `XML_PROCESSING_` environment variable prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| `XML_PROCESSING_MAX_FILE_SIZE_MB` | `20` | Maximum accepted file size in MB |
| `XML_PROCESSING_MAX_BATCH_SIZE` | `200` | Maximum files per batch operation |
| `XML_PROCESSING_ALLOWED_INPUT_DIRS` | `/input` | Comma-separated list of allowed input directories |
| `XML_PROCESSING_ALLOWED_OUTPUT_DIRS` | `/output` | Comma-separated list of allowed output directories |
| `XML_PROCESSING_INCLUDE_HEADERS_FOOTERS` | `false` | Include page headers and footers in output |
| `XML_PROCESSING_INCLUDE_COMMENTS` | `false` | Include document comments in output |
| `XML_PROCESSING_LOG_LEVEL` | `INFO` | Logging level |

---

## Source / Sink Extension Model

The pipeline is `Source → Parser → DocumentTree → Renderer → Sink`.

- **Add a new input source** — implement `DocumentSource` protocol (`get_document_bytes() -> bytes`). Candidates: `HttpSource`, `S3Source`, `SharePointSource`.
- **Add a new document format** — implement `DocumentParser` protocol (`parse(bytes) -> DocumentNode`). Planned: `PdfParser`, `HtmlParser`, `MarkdownParser`.
- **Add a new output format** — implement `DocumentRenderer` protocol (`render(DocumentNode) -> str`). Candidates: `JsonRenderer`, `MarkdownRenderer`.
- **Add a new output destination** — implement `XmlSink` protocol (`write_xml(id, xml) -> str | None`). Candidates: `HttpPostSink`, `S3Sink`, `N8nWebhookSink`.

---

## Development Commands

```bash
uv sync --group dev          # Install all dependencies including dev
uv run pytest                # Run tests with coverage
uv run ruff check src tests  # Lint
uv run ruff format src tests # Format
uv run mypy src              # Type check
```

---

## Security Notes

- Files above `MAX_FILE_SIZE_MB` are rejected before parsing.
- `.docm` (macro-enabled) files are always rejected.
- ZIP path traversal (`../`) is detected and rejected.
- ZIP bombs are guarded against via a 200 MB uncompressed size limit.
- XML is parsed with lxml (no external entity expansion, no network access during parse).
- File paths are validated against explicit allow-lists; path traversal via `resolve()` is blocked.
- Stack traces are never returned to the caller — errors surface as structured warnings.

---

## Roadmap

Possible future epics:

- PDF text and table extraction (`pymupdf`, `pdfplumber`)
- OCR pipeline for scanned PDFs
- HTML and Markdown parsers
- ODT parser
- XML post-processing and XSLT support
- JSON and Markdown renderers
- CV-specific document normalisation
- n8n and OpenAI agent workflow examples
- HTTP transport and authentication
- Kubernetes deployment manifests
