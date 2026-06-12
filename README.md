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
# Build and start (batch / stdio mode)
docker compose up --build

# Place .docx files in ./input, XML output appears in ./output
```

The container reads from `/input` (read-only) and writes to `/output`.

---

## Use with n8n

[n8n](https://n8n.io) is an open-source workflow automation tool. document-xml-mcp exposes
an HTTP/SSE endpoint when started with `MCP_TRANSPORT=sse`, which n8n connects to via its
**MCP Client Tool** node (available from n8n 1.28+).

```bash
# Start document-xml-mcp in SSE mode + n8n
MCP_TRANSPORT=sse docker compose --profile n8n up --build
```

Then open **http://localhost:5678**, import `n8n/workflows/parse-document.json`, add your
AI model credential, and POST a DOCX to the webhook.

→ **Full setup guide:** [docs/n8n-setup.md](docs/n8n-setup.md)

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

## Testing with MCP Inspector

[MCP Inspector](https://github.com/modelcontextprotocol/inspector) is an interactive browser-based UI for calling MCP tools manually. It requires Node.js (any recent LTS version).

### Launch

```bash
# Run against the local server — Inspector proxies stdio automatically
npx @modelcontextprotocol/inspector uv run document-xml-mcp
```

The command starts the server as a child process and opens the Inspector UI at `http://localhost:5173` (or prints the URL if that port is taken).

### Try each tool

**1. list_supported_document_types**

No inputs required. Expected response:
```json
{ "supported": ["docx"], "planned": ["pdf", "html", "markdown", "odt"] }
```

---

**2. parse_document_to_xml** — base64-encoded DOCX

Generate a base64 string from a `.docx` file using whichever shell you have available, then paste it into the `content_base64` field. Set `filename` to `cv.docx`.

#### Windows — PowerShell (built-in, no install needed)

```powershell
# Copy to clipboard
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\to\cv.docx")) | Set-Clipboard

# Print to terminal (pipe into Inspector field manually)
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\to\cv.docx"))
```

#### Windows — Command Prompt (CMD, built-in via certutil)

`certutil` adds a header/footer line; the one-liner below strips them:

```cmd
certutil -encode cv.docx cv.b64 && findstr /v /c:- cv.b64 > cv_clean.b64 && type cv_clean.b64
```

Or use Python if it is installed (see below).

#### Windows — Git Bash / WSL

`base64` is bundled with Git for Windows and available in all WSL distros without any extra install:

```bash
base64 -w 0 cv.docx | clip          # copy to Windows clipboard
base64 -w 0 cv.docx                 # print to terminal
```

#### Linux (pre-installed via GNU coreutils)

```bash
base64 -w 0 cv.docx                 # print (no line wrapping)
base64 -w 0 cv.docx | xclip -sel c  # copy (requires xclip: apt install xclip)
base64 -w 0 cv.docx | xsel --clipboard  # alternative clipboard tool
```

`base64` ships with every mainstream Linux distro. If somehow missing: `sudo apt install coreutils` / `sudo dnf install coreutils`.

#### macOS (pre-installed)

macOS ships BSD `base64`, which has a different flag set than the GNU version:

```bash
base64 -i cv.docx                   # print (BSD base64 wraps at 76 chars by default)
base64 -i cv.docx | tr -d '\n'      # strip newlines — required for MCP Inspector input
base64 -i cv.docx | tr -d '\n' | pbcopy   # copy to clipboard
```

> **Note:** The MCP Inspector `content_base64` field must receive a single unwrapped line. Always pipe through `tr -d '\n'` on macOS.

#### Any platform — Python (fallback, no extra install if Python is present)

```bash
python -c "import base64, sys; print(base64.b64encode(open(sys.argv[1],'rb').read()).decode())" cv.docx
```

Works identically on Windows PowerShell, CMD, Git Bash, Linux, and macOS.

Expected response shape:
```json
{
  "xml": "<document>\n  <body>\n    ...\n  </body>\n</document>\n",
  "warnings": [],
  "stats": { "source_type": "docx", "paragraph_count": 12, "table_count": 1, "character_count": 843 }
}
```

---

**3. parse_file_to_xml** — local file path

The project ships an `input/` directory (gitignored except `.gitkeep`) for test files.
Copy your DOCX there and use a project-relative path — no absolute paths or usernames needed:

```bash
# Copy your DOCX to the input/ directory
cp /path/to/cv.docx input/CV_Test_1.docx          # Linux / macOS / Git Bash
copy C:\path\to\cv.docx input\CV_Test_1.docx       # Windows CMD / PowerShell
```

Launch Inspector with `input` as the allowed directory (relative to the project root):

```bash
XML_PROCESSING_ALLOWED_INPUT_DIRS=input \
  npx @modelcontextprotocol/inspector uv run document-xml-mcp
```

Then call the tool with:
```json
{ "path": "input/CV_Test_1.docx" }
```

If the file is not found, verify the server's working directory is the project root (it is when launched with `uv run document-xml-mcp`).

---

**4. parse_batch_to_xml** — directory of DOCX files

```bash
XML_PROCESSING_ALLOWED_INPUT_DIRS=input \
XML_PROCESSING_ALLOWED_OUTPUT_DIRS=output \
  npx @modelcontextprotocol/inspector uv run document-xml-mcp
```

Call with:
```json
{ "input_dir": "input", "output_dir": "output", "continue_on_error": true }
```

Expected response shape:
```json
{ "processed": 3, "failed": 0, "results": [ ... ] }
```

### Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `warnings` contains "not within any allowed directory" | `path` or `input_dir` outside configured allow-list | Set `XML_PROCESSING_ALLOWED_INPUT_DIRS` to the correct path |
| `warnings` contains "exceeds limit" | File larger than `MAX_FILE_SIZE_MB` | Raise the limit via env var or use a smaller file |
| `warnings` contains "Unsupported file extension" | Non-DOCX file passed | Only `.docx` files are supported in this version |
| Inspector cannot connect | Server crashed on startup | Run `uv run document-xml-mcp` directly to see the error |

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
- n8n workflow examples ← see [docs/n8n-setup.md](docs/n8n-setup.md)
- OpenAI agent workflow examples
- HTTP transport and authentication
- Kubernetes deployment manifests
