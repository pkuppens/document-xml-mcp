# PLAN.md — document-xml-mcp MVP

Implements [Issue #1](https://github.com/pkuppens/document-xml-mcp/issues/1) using the MCP Python SDK per [Issue #2](https://github.com/pkuppens/document-xml-mcp/issues/2).

Pipeline: `Source → Parser → DocumentTree → Renderer → Sink`

---

## Milestone 1 — Project skeleton

### Task 1.1 — pyproject.toml and package structure

**Prompt:**
```
Create the Python package skeleton for `document-xml-mcp`.

Requirements:
- Use `uv` and `pyproject.toml` (no setup.py).
- Package name: `xml-processing-mcp`, importable as `xml_processing_mcp`.
- Python 3.12+.
- Source layout: `src/xml_processing_mcp/`.
- Dependencies: `mcp[cli]`, `lxml`, `defusedxml`, `pydantic`, `pydantic-settings`.
- Dev dependencies: `pytest`, `pytest-cov`, `ruff`, `mypy`.
- Add ruff config: line-length 132, target py312, select E/W/F/I/UP.
- Add mypy config: strict = false, ignore_missing_imports = true.
- Create these empty files with just a module docstring:
  src/xml_processing_mcp/__init__.py
  src/xml_processing_mcp/server.py
  src/xml_processing_mcp/config.py
  src/xml_processing_mcp/models.py
- Create tests/__init__.py (empty).
- Do NOT implement any logic yet.
```

### Task 1.2 — GitHub Actions CI

**Prompt:**
```
Add a GitHub Actions workflow at `.github/workflows/ci.yml`.

Requirements:
- Trigger on push and pull_request to main.
- Single job: lint-test.
- Steps:
  1. actions/checkout
  2. Install uv (astral-sh/setup-uv@v4)
  3. uv sync --group dev
  4. ruff check src tests
  5. ruff format --check src tests
  6. mypy src
  7. pytest --cov=xml_processing_mcp tests/
- Use ubuntu-latest and Python 3.12.
```

### Task 1.3 — Minimal MCP server entrypoint

**Prompt:**
```
Implement a minimal MCP server in `src/xml_processing_mcp/server.py` using the official MCP Python SDK.

Follow the FastMCP pattern from https://modelcontextprotocol.io/docs/develop/build-server.

Requirements:
- Create a `FastMCP` app named "document-xml-mcp".
- Register one stub tool: `list_supported_document_types` that returns
  {"supported": ["docx"], "planned": ["pdf", "html", "markdown", "odt"]}.
- Add `if __name__ == "__main__": mcp.run()` entry point.
- Add a `[project.scripts]` entry in pyproject.toml:
  `document-xml-mcp = "xml_processing_mcp.server:mcp.run"`.
- Write one test in `tests/test_server.py` that imports the server and asserts
  `list_supported_document_types` returns the expected dict.
- Verify: `uv run document-xml-mcp --help` should print MCP server help.
```

---

## Milestone 2 — Configuration and models

### Task 2.1 — Config

**Prompt:**
```
Implement `src/xml_processing_mcp/config.py` using pydantic-settings.

Fields (all with safe defaults):
- max_file_size_mb: int = 20
- max_batch_size: int = 200
- allowed_input_dirs: list[str] = ["/input"]
- allowed_output_dirs: list[str] = ["/output"]
- include_headers_footers: bool = False
- include_comments: bool = False
- log_level: str = "INFO"

Env prefix: `XML_PROCESSING_`.

Add `tests/test_config.py` that:
1. Verifies default values.
2. Verifies env-var override works (monkeypatch).
```

### Task 2.2 — Pydantic models

**Prompt:**
```
Implement `src/xml_processing_mcp/models.py` with these Pydantic v2 models:

Request models:
- ParseDocumentRequest: filename (str), content_base64 (str), document_type (str = "docx"), profile (str = "generic")
- ParseFileRequest: path (str), document_type (str = "docx"), profile (str = "generic")
- ParseBatchRequest: input_dir (str), output_dir (str), document_type (str = "docx"), continue_on_error (bool = True)

Response models:
- ParseStats: source_type (str), paragraph_count (int), table_count (int), character_count (int)
- ParseDocumentResponse: xml (str), warnings (list[str]), stats (ParseStats)
- ParseBatchResult: filename (str), output_path (str | None), warnings (list[str]), error (str | None = None)
- ParseBatchResponse: processed (int), failed (int), results (list[ParseBatchResult])
- SupportedTypesResponse: supported (list[str]), planned (list[str])

Add `tests/test_models.py` with basic construction and serialization tests.
```

---

## Milestone 3 — Source and Sink abstractions

### Task 3.1 — Sources

**Prompt:**
```
Implement sources in `src/xml_processing_mcp/sources/`.

Files to create:
- __init__.py
- base.py  — DocumentSource Protocol with `get_document_bytes() -> bytes`
- bytes_source.py  — BytesSource(bytes) and Base64Source(str) implementing the protocol
- file_source.py  — FileSource(path: str, allowed_dirs: list[str]) implementing the protocol;
  raises ValueError on path traversal or disallowed directory

Add `tests/test_sources.py`:
- BytesSource returns the bytes unchanged.
- Base64Source decodes correctly.
- FileSource reads a real temp file.
- FileSource raises ValueError for a path outside allowed dirs.
- FileSource raises ValueError for path traversal (../../etc/passwd).
```

### Task 3.2 — Sinks

**Prompt:**
```
Implement sinks in `src/xml_processing_mcp/sinks/`.

Files to create:
- __init__.py
- base.py  — XmlSink Protocol with `write_xml(document_id: str, xml: str) -> str | None`
- return_sink.py  — ReturnSink stores xml in memory, write_xml returns the xml string
- file_sink.py  — FileSink(output_dir: str, allowed_dirs: list[str]);
  write_xml writes `<output_dir>/<document_id>.xml`, raises ValueError for disallowed dirs

Add `tests/test_sinks.py`:
- ReturnSink returns the xml string.
- FileSink writes a file to a temp dir.
- FileSink raises ValueError for a disallowed output dir.
```

---

## Milestone 4 — Document tree

### Task 4.1 — Tree nodes

**Prompt:**
```
Implement `src/xml_processing_mcp/document_tree/nodes.py`.

Use a single dataclass:

    @dataclass
    class DocumentNode:
        tag: str
        text: str | None = None
        attributes: dict[str, str] = field(default_factory=dict)
        children: list["DocumentNode"] = field(default_factory=list)

Also define a module-level TAG_NAMES list with valid tags:
"document", "body", "section", "heading", "paragraph",
"list", "item", "table", "row", "cell", "link", "break", "unknown"

Create `src/xml_processing_mcp/document_tree/__init__.py` (empty).
Create `src/xml_processing_mcp/document_tree/builder.py` with a single helper:
`def make_node(tag: str, text: str | None = None, **attrs: str) -> DocumentNode`

Add `tests/test_document_tree.py`:
- make_node creates a node with correct tag, text, and attrs.
- Children can be appended.
```

---

## Milestone 5 — Security checks

### Task 5.1 — File and ZIP safety

**Prompt:**
```
Implement security helpers in `src/xml_processing_mcp/security/`.

Files:
- __init__.py
- file_limits.py:
  - `check_file_size(data: bytes, max_mb: int) -> None` — raises ValueError if too large
  - `check_extension(filename: str, allowed: list[str] = [".docx"]) -> None` — raises ValueError for disallowed or .docm
- zip_safety.py:
  - `safe_open_docx(data: bytes) -> zipfile.ZipFile` — opens and validates:
    - It is a valid ZIP.
    - No entry has a path traversal (`..` in name).
    - Total uncompressed size < 200 MB (hard-coded bomb guard).
    - Returns the ZipFile object.

Add `tests/test_security.py`:
- Oversized bytes raise ValueError.
- .docm raises ValueError.
- A valid in-memory DOCX (built with zipfile) passes.
- A ZIP with a `../evil` entry raises ValueError.
- A ZIP bomb (large declared uncompressed size) raises ValueError.
```

---

## Milestone 6 — DOCX parser

### Task 6.1 — DOCX parser

**Prompt:**
```
Implement `src/xml_processing_mcp/parsers/docx_parser.py`.

Create `DocxParser` with a single public method:
  `def parse(self, document_bytes: bytes) -> DocumentNode`

Implementation steps inside parse():
1. Call `safe_open_docx(document_bytes)` from security.zip_safety.
2. Read `word/document.xml` from the ZIP.
3. Parse with `lxml.etree.fromstring` (bytes).
4. Walk the element tree and map WordprocessingML to DocumentNode:
   - `w:p` → paragraph or heading (check `w:pStyle` val; heading if style starts with "Heading")
   - `w:tbl` → table; `w:tr` → row; `w:tc` → cell
   - `w:numPr` presence → mark paragraph as list item (tag = "item"); wrap consecutive items in a "list" node
   - `w:hyperlink` → link node (use `r:id` as href attribute if present)
   - Collect all `w:t` text within a `w:p` and join them as the node's text
5. Wrap everything in DocumentNode(tag="document") > DocumentNode(tag="body").
6. Return the document node.

Create `src/xml_processing_mcp/parsers/__init__.py` (empty).
Create `src/xml_processing_mcp/parsers/base.py` — DocumentParser Protocol with `parse(bytes) -> DocumentNode`.

Add fixture directory `tests/fixtures/`.
Add `tests/test_docx_parser.py`:
- Build a minimal in-memory DOCX using zipfile + a hardcoded word/document.xml string
  containing: one heading, two paragraphs, one 2x2 table, one list item, one hyperlink.
- Assert paragraphs appear in document order.
- Assert heading node has tag "heading".
- Assert table node has two row children, each with two cell children.
- Assert at least one item node exists.
```

---

## Milestone 7 — XML renderer (tree processor)

### Task 7.1 — SimpleXmlRenderer

**Prompt:**
```
Implement `src/xml_processing_mcp/renderers/simple_xml_renderer.py`.

`SimpleXmlRenderer` is a tree processor, not just a serialiser. It cleans the
DocumentNode tree before emitting XML by applying these rules in a single
recursive pass:

1. **Remove empty nodes** — drop any node where text is None or whitespace-only
   AND it has no children.
2. **Strip useless attributes** — remove any attribute whose value is empty,
   "none", "false", or "0" (case-insensitive). Keep "level" on heading nodes
   regardless of value.
3. **Promote single-child nodes** — if a node has exactly one child, no text,
   and no attributes after stripping, replace the node with its child in the
   parent's children list (unwrap the wrapper).

After cleaning, serialise the resulting tree to XML using lxml.etree:
  `lxml.etree.tostring(root, pretty_print=True, encoding="unicode")`

Public API:
  `def render(self, document: DocumentNode) -> str`

Create `src/xml_processing_mcp/renderers/__init__.py` (empty).
Create `src/xml_processing_mcp/renderers/base.py` — DocumentRenderer Protocol:
  `def render(self, document: DocumentNode) -> str`

Add `tests/test_simple_xml_renderer.py`:
- An empty-text node with no children is removed from output.
- A useless attribute (empty string value) is stripped.
- A wrapper node with one child and no text/attrs is replaced by its child.
- A heading node keeps its "level" attribute even if value is "0".
- The final output is valid XML (parseable by lxml).
- A minimal realistic tree (heading + paragraph + table) round-trips correctly.
```

---

## Milestone 8 — Service layer

### Task 8.1 — DocumentProcessingService

**Prompt:**
```
Implement `src/xml_processing_mcp/services/document_processing_service.py`.

Create `DocumentProcessingService(config: Settings)` with:

  def process(
      self,
      source: DocumentSource,
      filename: str,
      parser: DocumentParser | None = None,
      sink: XmlSink | None = None,
  ) -> ParseDocumentResponse

Logic:
1. data = source.get_document_bytes()
2. check_file_size(data, config.max_file_size_mb)
3. check_extension(filename)
4. parser = parser or DocxParser()
5. tree = parser.parse(data)
6. renderer = SimpleXmlRenderer()
7. xml = renderer.render(tree)
8. Walk the tree to count paragraphs and tables for stats.
9. sink = sink or ReturnSink()
10. sink.write_xml(filename, xml)
11. Return ParseDocumentResponse(xml=xml, warnings=[], stats=ParseStats(...))

Create `src/xml_processing_mcp/services/__init__.py` (empty).

Add `tests/test_document_processing_service.py`:
- Use BytesSource with in-memory minimal DOCX bytes.
- Assert response.xml is non-empty and parseable by lxml.
- Assert stats.paragraph_count >= 0.
- Pass a custom sink and assert write_xml was called with the xml string.
```

---

## Milestone 9 — MCP tools (full)

### Task 9.1 — Wire up all four MCP tools

**Prompt:**
```
Replace the stub in `src/xml_processing_mcp/server.py` with the four full MCP tools.
Use the FastMCP pattern from the MCP Python SDK.

Tools to implement:

1. list_supported_document_types() -> SupportedTypesResponse
   Return {"supported": ["docx"], "planned": ["pdf", "html", "markdown", "odt"]}.

2. parse_document_to_xml(req: ParseDocumentRequest) -> ParseDocumentResponse
   - Build Base64Source(req.content_base64).
   - Call DocumentProcessingService(get_settings()).process(source, req.filename).
   - Return response.

3. parse_file_to_xml(req: ParseFileRequest) -> ParseDocumentResponse
   - Build FileSource(req.path, get_settings().allowed_input_dirs).
   - Call service.process(source, Path(req.path).name).
   - Return response.

4. parse_batch_to_xml(req: ParseBatchRequest) -> ParseBatchResponse
   - Validate req.input_dir is within allowed_input_dirs.
   - List all .docx files in req.input_dir.
   - For each file: build FileSource, call service with FileSink(req.output_dir, allowed_output_dirs).
   - Collect results; if error and not continue_on_error, raise immediately.
   - Return ParseBatchResponse with processed/failed counts and per-file results.

Catch all exceptions from the service layer and return them as warnings or
raise McpError with a structured message — never leak stack traces.

Add `tests/test_mcp_tools.py`:
- list_supported_document_types returns the expected dict.
- parse_document_to_xml with a valid base64 DOCX returns non-empty xml.
- parse_file_to_xml with a path outside allowed_input_dirs returns an error.
```

---

## Milestone 10 — Docker and README

### Task 10.1 — Dockerfile and docker-compose

**Prompt:**
```
Add a Dockerfile and docker-compose.yml for document-xml-mcp.

Dockerfile requirements:
- Base image: python:3.12-slim.
- Install uv via pip.
- Copy pyproject.toml and src/.
- Run `uv sync --no-dev`.
- Create non-root user `appuser` and switch to it.
- WORKDIR /app.
- CMD: ["uv", "run", "document-xml-mcp"]

docker-compose.yml:
- Service: document-xml-mcp.
- Build from Dockerfile.
- Volumes: ./input:/input:ro, ./output:/output.
- Environment: XML_PROCESSING_ALLOWED_INPUT_DIRS=/input, XML_PROCESSING_ALLOWED_OUTPUT_DIRS=/output.

Create empty `input/.gitkeep` and `output/.gitkeep`.
Add `input/` and `output/` to .gitignore (but keep the .gitkeep files tracked).
```

### Task 10.2 — README

**Prompt:**
```
Rewrite README.md for document-xml-mcp.

Sections to include:
1. Project purpose — one paragraph: DOCX in, simplified semantic XML out, MCP server.
2. Current scope: DOCX supported now, PDF planned.
3. Quickstart: `uv sync && uv run document-xml-mcp`.
4. Run with Docker (using docker-compose.yml).
5. MCP tool reference: table with tool name, description, key inputs/outputs.
6. Example XML output (use the sample from the issue: Jane Doe CV snippet).
7. Configuration: table of all XML_PROCESSING_ env vars with defaults.
8. Source / Sink extension model — brief 3-4 bullet points.
9. Development commands: sync, test, lint, format, mypy.
10. Security notes: ZIP safety, size limits, no external XML entities.
11. Roadmap — brief bullet list of future epics.

Keep it factual — do not claim PDF support is implemented.
```

---

## Definition of Done

- [ ] `uv run pytest` passes
- [ ] `uv run ruff check src tests` clean
- [ ] `uv run ruff format --check src tests` clean
- [ ] `uv run mypy src` clean
- [ ] `docker build .` succeeds
- [ ] CI workflow passes on push
- [ ] All four MCP tools callable from an MCP client
