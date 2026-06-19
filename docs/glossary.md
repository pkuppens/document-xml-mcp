# MCP Glossary — document-xml-mcp

This glossary defines the MCP (Model Context Protocol) primitives and project-specific concepts used in this codebase. Every design decision about what goes where should be traceable to these definitions.

---

## MCP Primitives

### Tool

A **server-side function** that the LLM invokes to perform computation or trigger side effects.

| Aspect | Detail |
|--------|--------|
| **Who defines it** | MCP server (via `@mcp.tool()`) |
| **Who calls it** | LLM (client-side, inside a conversation turn) |
| **Who executes it** | MCP server |
| **Has side effects?** | Yes — may write files, call APIs, modify state |
| **Returns** | Structured data (JSON, text) the LLM reads |

**When to use:** Any operation that requires computation, data retrieval, or side effects that the LLM cannot perform itself.

**Project examples:**
- `parse_document_to_xml(filename, content_base64)` — decodes and parses DOCX bytes → clean XML
- `parse_file_to_xml(path)` — reads a file from the server's filesystem and parses it
- `parse_batch_to_xml(input_dir, output_dir)` — processes a directory of DOCX files
- `extract_cv_fields(xml)` *(proposed)* — parses CV XML → structured JSON

**Anti-pattern:** Wrapping an LLM call inside a tool. If the "computation" is just prompting an LLM, expose a Prompt instead — it's cheaper, faster, and more transparent.

---

### Prompt

A **reusable instruction template** that the server exposes for clients to retrieve and apply to an LLM.

| Aspect | Detail |
|--------|--------|
| **Who defines it** | MCP server (via `@mcp.prompt()`) |
| **Who retrieves it** | MCP client (calls `prompts/get`) |
| **Who executes it** | LLM (the client sends the prompt messages to the LLM) |
| **Has side effects?** | No — the server only returns text |
| **Returns** | A list of `PromptMessage` objects (role + content) |

**When to use:** Reusable LLM instruction patterns that benefit from central versioning and cross-client discoverability. The LLM does the work; the server provides the recipe.

**Key distinction from Tool:** The server does NOT call an LLM. It returns the prompt text, and the client/LLM executes it.

**Project examples (proposed):**
- `analyze_cv_gaps(cv_xml, job_description)` — instructs LLM to identify skill/experience gaps
- `write_motivation_letter(cv_xml, assignment, tone)` — instructs LLM to write a letter
- `rewrite_cv_for_assignment(cv_xml, assignment)` — instructs LLM to tailor a CV
- `answer_cv_questions(cv_xml, question)` — instructs LLM to answer questions about a CV

**Not a prompt:**
- Operations that require computation (parsing XML, reading files) → use a Tool
- Static reference data (schemas, templates) → use a Resource

---

### Resource

A **piece of data** the LLM reads as context, identified by a URI.

| Aspect | Detail |
|--------|--------|
| **Who defines it** | MCP server (via `@mcp.resource(uri)`) |
| **Who reads it** | MCP client (calls `resources/read`) |
| **Who uses it** | LLM (receives the content as context) |
| **Has side effects?** | No — read-only |
| **Returns** | Raw content (text, XML, JSON, binary) with a MIME type |

**When to use:** Reference data the LLM needs to read before or during generation — schemas, templates, examples, configuration that defines expected structure.

**Key distinction from Prompt:** A Resource is *data to read*; a Prompt is *instructions to follow*.

| Question | Resource | Prompt |
|----------|----------|--------|
| Does the LLM read it as context? | ✓ | — |
| Does the LLM follow it as instructions? | — | ✓ |
| Is it a schema or structural definition? | ✓ | — |
| Is it a workflow or task description? | — | ✓ |
| Does it have a URI? | ✓ | — |

**Project examples (proposed):**
- `cv://templates/export-schema` — XML schema for the target CV structure; LLM reads this to know what to output
- `cv://templates/assignment-format` — example/schema for job descriptions; LLM reads this to parse assignments

---

## MCP Architecture

### MCP Server

A process that exposes Tools, Prompts, and/or Resources over the MCP protocol. Clients connect to it and invoke its capabilities.

**This project's server:** `src/xml_processing_mcp/server.py` — a `FastMCP` application.

**Transport options:**
- `stdio` — spawned as child process; used for local Claude Desktop / MCP Inspector
- `sse` — HTTP Server-Sent Events on port 8000; used for Docker, n8n, remote clients
- `streamable-http` — HTTP streaming variant

**Single responsibility of this server:** Convert DOCX documents to clean, structured XML. See [ADR-005](adr/ADR-005-cv-intelligence-server-boundary.md).

---

### MCP Client

Any application that connects to an MCP server and invokes its Tools, Prompts, and Resources. Clients send requests; servers respond.

**Clients of this project:**
- `examples/client_stdio.py` — Python client that spawns the server and calls all tools
- `examples/client_sse.py` — Python client connecting over HTTP/SSE
- Claude Desktop — GUI client that can connect via stdio or SSE
- n8n — workflow automation platform; calls tools via HTTP MCP node

**The LLM itself is a client** (when used inside Claude Desktop or the Claude API). The LLM sees tool definitions, decides when to call them, and incorporates results into its responses.

---

## Pipeline Abstractions (Project-Specific)

### Source

Provides raw document bytes to the processing pipeline. Implements the `DocumentSource` protocol: `get_document_bytes() → bytes`.

| Implementation | When used |
|---------------|-----------|
| `Base64Source` | Client sends file content as base64 string (default for `parse_document_to_xml`) |
| `FileSource` | File already on server filesystem (used by `parse_file_to_xml`, `parse_batch_to_xml`) |
| `BytesSource` | In-memory bytes; used in tests |

**Extensible to:** `HttpSource` (fetch from URL), `S3Source`, `SharePointSource`.

---

### Sink

Receives the processed XML and writes it to a destination. Implements the `XmlSink` protocol: `write_xml(id, xml) → str | None`.

| Implementation | When used |
|---------------|-----------|
| `ReturnSink` | Holds XML in memory for return to client (default) |
| `FileSink` | Writes XML to a file on server filesystem (used by batch) |

**Extensible to:** `DatabaseSink`, `HttpPostSink`, `S3Sink`. Whether these belong in this server is a scope decision — see [ADR-004](adr/ADR-004-tool-side-effects-and-server-boundary.md).

---

### DocumentNode

The internal tree representation of a parsed document. A recursive dataclass: `tag`, `text`, `attributes`, `children`.

Tags: `document`, `body`, `section`, `heading`, `paragraph`, `list`, `item`, `table`, `row`, `cell`, `link`, `break`, `unknown`.

Parsers produce `DocumentNode` trees; renderers consume them to produce XML strings.

---

### DocumentParser

Protocol that converts raw bytes to a `DocumentNode` tree: `parse(bytes) → DocumentNode`.

Current implementation: `DocxParser` (DOCX → XML via `lxml`). Extensible to `PdfParser`, `HtmlParser`.

---

### DocumentRenderer

Protocol that converts a `DocumentNode` tree to a string: `render(DocumentNode) → str`.

Current implementation: `SimpleXmlRenderer` — applies three cleanup rules (remove empties, strip useless attributes, promote single-child nodes) then serializes to pretty-printed XML.

---

## Decision Table: Which Primitive Fits?

Given a use case, which MCP primitive should it be?

| Use case | Primitive | Reason |
|----------|-----------|--------|
| Parse DOCX → XML | Tool | Computation, server executes it |
| Extract structured fields from XML | Tool | Computation, no LLM needed |
| Analyze CV gaps vs job description | Prompt | LLM executes; server provides the recipe |
| Write a motivation letter | Prompt | LLM generates text; server provides instructions |
| Rewrite CV for a specific assignment | Prompt | LLM generates text; server provides instructions |
| Answer a question about a CV | Prompt | LLM reasons; server provides the framing |
| CV XML export schema (target structure) | Resource | Reference data LLM reads, not follows |
| Assignment description format | Resource | Reference data LLM reads, not follows |
| Write CV to database | Tool (or client) | Side effect; see ADR-004 for ownership |
| List supported document types | Tool | Lightweight metadata query |
