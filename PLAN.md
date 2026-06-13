# PLAN.md — document-xml-mcp

Pipeline: `Source → Parser → DocumentTree → Renderer → Sink`

---

## Phase 1 — MVP (COMPLETE ✓)

All milestones below are implemented, tested (100% coverage), linted, and committed.

| Milestone | Description | Status |
|-----------|-------------|--------|
| 1 — Skeleton | pyproject.toml, package layout, CI | ✓ |
| 2 — Config & Models | pydantic-settings, request/response models | ✓ |
| 3 — Sources & Sinks | BytesSource, Base64Source, FileSource, ReturnSink, FileSink | ✓ |
| 4 — Document tree | DocumentNode, make_node | ✓ |
| 5 — Security | file size / extension / ZIP-bomb guards | ✓ |
| 6 — DOCX parser | DocxParser (heading, paragraph, list, table, link) | ✓ |
| 7 — XML renderer | SimpleXmlRenderer (clean + serialise) | ✓ |
| 8 — Service layer | DocumentProcessingService | ✓ |
| 9 — MCP tools | All four tools wired in server.py | ✓ |
| 10 — Docker & README | Dockerfile, docker-compose, README | ✓ |

### Definition of Done — Phase 1

- [x] `uv run pytest` — 86 tests pass, 100% coverage
- [x] `uv run ruff check src tests` — clean
- [x] `uv run ruff format --check src tests` — clean
- [x] `uv run mypy src` — clean
- [x] `docker build .` succeeds
- [x] CI workflow passes on push
- [x] All four MCP tools callable from MCP Inspector

---

## Phase 2 — Production Hardening

Small, independently shippable tasks ordered by dependency. Each task has explicit
pre-conditions and acceptance criteria. No task exceeds ~2 hours of implementation.

---

### Milestone 11 — Config: env-var robustness (COMPLETE ✓)

**Already shipped as part of Phase 2 kickoff.**

Fixed a bug where `allowed_input_dirs` and `allowed_output_dirs` could not be set
from plain path strings or comma-separated strings via environment variables
(pydantic-settings v2 requires JSON for list fields by default).

Fix: `NoDecode` annotation + `field_validator` accepting plain path, comma-separated
string, or JSON array. Default `log_level` corrected from `"DEBUG"` to `"INFO"`.

---

### Milestone 12 — Real-file regression test

#### Task 12.1 — Smoke test with the real CV fixture

**Pre-conditions:**
- `input/CV_Test_1.docx` exists in the repo.
- All Phase 1 tests pass.

**Prompt:**
```
Add `tests/test_real_docx.py`.

Use the actual file `input/CV_Test_1.docx` (checked in to the repo) as a fixture.
The test must:
1. Read the file bytes.
2. Call `DocumentProcessingService(Settings()).process(BytesSource(data), "CV_Test_1.docx")`.
3. Assert `resp.xml` is non-empty and parseable by lxml.
4. Assert `resp.stats.paragraph_count > 0`.
5. Assert `resp.stats.table_count > 0`.
6. Assert `resp.warnings == []`.
7. Assert the XML string contains `<document>` and `</document>`.

Mark the test with `@pytest.mark.real_file` (add the marker to pyproject.toml).

Do NOT mock anything — this is a real integration test against the real file.
```

**Acceptance criteria:**
- [ ] Test runs with `uv run pytest -m real_file`.
- [ ] Test passes with the committed `CV_Test_1.docx`.
- [ ] Coverage stays at 100%.

---

#### Task 12.2 — Golden-file XML snapshot

**Pre-conditions:**
- Task 12.1 is complete (real-file test passes).

**Prompt:**
```
Add a snapshot test in `tests/test_real_docx.py`.

Steps:
1. Parse `input/CV_Test_1.docx` to XML using the service layer (same as Task 12.1).
2. Write the output to `tests/fixtures/CV_Test_1_golden.xml` if the file does not exist
   (first-run auto-generate).
3. On subsequent runs, assert the current output equals the file contents.
4. Add `tests/fixtures/CV_Test_1_golden.xml` to `.gitignore` so it is generated locally
   but not committed.

Purpose: catch accidental changes to parsing or rendering logic.
```

**Acceptance criteria:**
- [ ] Running the test twice produces the same output.
- [ ] Modifying the renderer causes the test to fail on the second run.
- [ ] The golden file is gitignored.

---

### Milestone 13 — Parser edge cases

#### Task 13.1 — Empty and whitespace-only documents

**Pre-conditions:**
- Phase 1 complete. Synthetic DOCX builder pattern from `tests/test_docx_parser.py`.

**Prompt:**
```
Add `tests/test_parser_edge_cases.py` with the following tests.
Each test builds a minimal in-memory DOCX using `zipfile.ZipFile + io.BytesIO`,
feeding the raw XML directly into `DocxParser().parse(bytes)`.

Tests:
1. `test_empty_body` — document.xml has `<w:body/>` (no children).
   Assert parser returns `DocumentNode(tag="document")` with one "body" child.
   Assert the renderer produces `<document><body/></document>` or `<document/>`.

2. `test_whitespace_only_paragraphs` — body with 3 `<w:p>` elements containing
   only whitespace `<w:t>  </w:t>`.
   Assert renderer output does not contain any `<paragraph>` element
   (empty-text nodes must be dropped by the renderer Rule 1).

3. `test_paragraph_with_empty_runs` — `<w:p>` with `<w:r/>` (run with no w:t).
   Assert the paragraph is dropped (no text → Rule 1 removes it).

4. `test_table_with_empty_cells` — 2×2 table where all cells have empty text.
   Assert that the table element IS present in the output (tables are non-promotable)
   but cells with no text are dropped (Rule 1).

5. `test_no_body_element` — document.xml has no `<w:body>` at all.
   Assert parser returns a document node with an empty body child (defensive fallback).
```

**Acceptance criteria:**
- [ ] All 5 tests pass.
- [ ] Coverage stays at 100%.
- [ ] No new production code changes needed (edge cases handled by existing logic).

---

#### Task 13.2 — Heading style variants

**Pre-conditions:**
- Task 13.1 complete.

**Prompt:**
```
Add tests to `tests/test_parser_edge_cases.py` for heading style detection.

DOCX heading styles vary across Word versions:
- "Heading1" (no space, camelCase) — most common
- "Heading 1" (with space) — older Word
- "heading1" (lowercase) — some generators

Current parser: `style.startswith("Heading") or style.startswith("heading")`

Tests to add:
1. `test_heading_style_no_space` — pStyle val="Heading1" → tag="heading", level="1".
2. `test_heading_style_with_space` — pStyle val="Heading 1" → NOT a heading
   (current logic: "Heading 1".startswith("Heading") is True, but level extraction
   `''.join(c for c in style if c.isdigit())` gives "1" from "Heading 1" correctly).
   Assert tag="heading" and level="1".
3. `test_heading_style_lowercase` — pStyle val="heading2" → tag="heading", level="2".
4. `test_non_heading_style` — pStyle val="Title" → tag="paragraph" (not a heading).
5. `test_heading_level_extraction` — pStyle val="Heading10" → level="10".

If any test exposes a bug, fix the parser and update this task note.
```

**Acceptance criteria:**
- [ ] All 5 tests pass.
- [ ] Level extraction correctly handles double-digit levels.
- [ ] `uv run mypy src` clean.

---

#### Task 13.3 — List grouping and continuity

**Pre-conditions:**
- Task 13.1 complete.

**Prompt:**
```
Add tests to `tests/test_parser_edge_cases.py` for list grouping behaviour.

The parser groups consecutive list items into a single `<list>` node and resets
`pending_list` when a non-list element is encountered.

Tests to add:
1. `test_list_items_grouped` — 3 consecutive list items → one `<list>` with 3 `<item>` children.
2. `test_list_interrupted_by_paragraph` — list item, paragraph, list item
   → two separate `<list>` nodes each with one `<item>`.
3. `test_list_item_empty_text` — list item with empty w:t → item is NOT added
   (empty items are dropped by the renderer, not the parser; verify via rendered XML).
4. `test_list_followed_by_table` — list item then table → list then table in output,
   in that order.
```

**Acceptance criteria:**
- [ ] All 4 tests pass.
- [ ] Coverage stays at 100%.

---

### Milestone 14 — Service layer edge cases

#### Task 14.1 — File size boundary conditions

**Pre-conditions:**
- Phase 1 complete. `check_file_size` in `security/file_limits.py`.

**Prompt:**
```
Add `tests/test_service_edge_cases.py` with boundary tests for `check_file_size`.

Tests:
1. `test_file_exactly_at_limit` — data of exactly `max_mb * 1024 * 1024` bytes.
   Assert `check_file_size(data, max_mb)` does NOT raise.
2. `test_file_one_byte_over_limit` — data of `max_mb * 1024 * 1024 + 1` bytes.
   Assert `check_file_size(data, max_mb)` raises `ValueError`.
3. `test_service_rejects_oversized_base64` — create a base64-encoded byte string
   representing a file 1 byte over the 20 MB limit. Call `parse_document_to_xml`
   via the tool function and assert it raises `ValueError`.
4. `test_empty_batch_dir` — call `parse_batch_to_xml` with an empty directory
   (no .docx files). Assert `processed=0`, `failed=0`, `results=[]`.
5. `test_batch_mixed_good_bad` — directory with one valid DOCX and one invalid
   (corrupt ZIP) DOCX. Assert `processed=1`, `failed=1`, `continue_on_error=True`.
```

**Acceptance criteria:**
- [ ] All 5 tests pass.
- [ ] Coverage stays at 100%.

---

#### Task 14.2 — Corrupt DOCX handling

**Pre-conditions:**
- Task 14.1 complete.

**Prompt:**
```
Add tests to `tests/test_service_edge_cases.py` for corrupt / malformed DOCX input.

Tests:
1. `test_valid_zip_missing_document_xml` — ZIP that does not contain `word/document.xml`.
   Assert the parser raises a `KeyError` (ZipFile.read() on a missing entry).
   Assert this propagates through DocumentProcessingService as an exception.

2. `test_valid_zip_malformed_document_xml` — ZIP where `word/document.xml` contains
   malformed XML (`<broken>`). Assert the parser raises an `lxml.etree.XMLSyntaxError`.
   Assert this propagates through DocumentProcessingService as an exception.

3. `test_not_a_zip` — bytes that are not a ZIP at all (e.g. `b"hello world"`).
   Assert `safe_open_docx` raises `zipfile.BadZipFile`.

Ensure the service layer does NOT swallow these — they should propagate to the tool
boundary where the `except Exception` in server.py logs and re-raises.
```

**Acceptance criteria:**
- [ ] All 3 tests pass.
- [ ] No new production code needed — tests verify existing error propagation.

---

### Milestone 15 — Integration tests (subprocess)

#### Task 15.1 — Stdio subprocess integration test

**Pre-conditions:**
- Phase 1 complete. `uv run document-xml-mcp` launches successfully.
- Python `asyncio` and `mcp` SDK available in dev dependencies.

**Prompt:**
```
Add `tests/test_integration_stdio.py`.

These tests launch the actual MCP server as a subprocess via `StdioServerParameters`
and call tools over the real MCP protocol. Mark all tests with
`@pytest.mark.integration` and `@pytest.mark.slow` so they can be skipped in fast runs.

Add these markers to `pyproject.toml` under `[tool.pytest.ini_options]`:
  markers = [
    "real_file: tests using checked-in fixture files",
    "integration: tests that launch the server as a subprocess",
    "slow: tests that take more than 1 second",
  ]

Tests:
1. `test_stdio_list_supported_types` — connect via stdio, call
   `list_supported_document_types`, assert `supported == ["docx"]`.

2. `test_stdio_parse_document_to_xml_valid` — connect via stdio, call
   `parse_document_to_xml` with the base64-encoded bytes from `_make_docx_bytes()`
   (the minimal synthetic DOCX from `test_mcp_tools.py`). Assert xml is non-empty.

3. `test_stdio_parse_file_disallowed_path` — connect via stdio (allowed_input_dirs
   set to a tmp dir), call `parse_file_to_xml` with `/etc/passwd`. Assert the
   CallToolResult has `isError=True` or contains an error message.

Each test must use `asyncio.run()` or `pytest-asyncio`. Use the existing
`StdioServerParameters` pattern from `examples/client_stdio.py`.

Add `pytest-asyncio` to dev dependencies in pyproject.toml if not present.
```

**Acceptance criteria:**
- [ ] Tests are skipped with `uv run pytest -m "not integration"`.
- [ ] Tests pass with `uv run pytest -m integration`.
- [ ] Tests verify the real MCP protocol round-trip, not just function calls.
- [ ] No mocking of the server — real subprocess, real protocol.

---

### Milestone 16 — SSE transport and Docker validation

#### Task 16.1 — SSE transport startup test

**Pre-conditions:**
- Phase 1 complete. `MCP_TRANSPORT=sse uv run document-xml-mcp` starts a server.

**Prompt:**
```
Add `tests/test_sse_transport.py`.

Mark all tests `@pytest.mark.integration` and `@pytest.mark.slow`.

Tests:
1. `test_sse_server_starts_and_accepts_connection` — start the server in SSE mode
   on a free port using `subprocess.Popen`, wait up to 5 seconds for it to be ready
   (check via `socket.create_connection`), then:
   - Connect with `sse_client(f"http://localhost:{port}/sse")`.
   - Call `list_supported_document_types`.
   - Assert result.
   - Kill the server process.

Use `pytest.fixture` with `scope="module"` to start/stop the server once for all
tests in this file.
```

**Acceptance criteria:**
- [ ] Test passes when run on a machine with `uv` installed.
- [ ] Test properly kills the server process in teardown (no orphan processes).
- [ ] Skipped with `uv run pytest -m "not integration"`.

---

#### Task 16.2 — Fix docker-compose healthcheck for stdio mode

**Pre-conditions:**
- Docker available locally.

**Context:**
The current `docker-compose.yml` healthcheck tries to TCP-connect to port 8000.
This port is only open in SSE mode (`MCP_TRANSPORT=sse`). In the default stdio mode
the server reads from stdin; there is no listening socket, so the healthcheck always
reports unhealthy.

**Prompt:**
```
Fix `docker-compose.yml` to make the healthcheck mode-aware.

Option A (simplest): Remove the healthcheck from the `document-xml-mcp` service
for stdio mode. Add a comment explaining the healthcheck only applies to SSE mode.
Override the healthcheck to a no-op or remove it entirely for the default stdio service,
and add a separate SSE-mode service override or profile.

Option B: Add a separate docker-compose.override.sse.yml that adds the healthcheck and
sets `MCP_TRANSPORT=sse`. The base docker-compose.yml has no healthcheck.

Recommended: Option A — simpler, fewer files.

After the change:
- `docker compose up` (stdio mode) starts without health warnings.
- The n8n profile (SSE mode) retains a working healthcheck.
- Update README to clarify the healthcheck behaviour.
```

**Acceptance criteria:**
- [ ] `docker compose up` in stdio mode shows status `Up` (not `Up (unhealthy)`).
- [ ] `docker compose --profile n8n up` still performs a real healthcheck.
- [ ] README updated.

---

#### Task 16.3 — streamable-http transport support

**Pre-conditions:**
- Phase 1 complete. FastMCP supports `transport="streamable-http"` (MCP 1.x+).

**Context:**
FastMCP 1.27 exposes a third transport, `streamable-http`, which uses HTTP POST
for sending and streaming for responses. This is the recommended transport for
new HTTP-based MCP deployments (replaces SSE). The server currently supports only
`stdio` and `sse`.

**Prompt:**
```
Extend `src/xml_processing_mcp/server.py` to support `MCP_TRANSPORT=streamable-http`.

In the `run()` function, add a third branch:
  elif transport == "streamable-http":
      os.environ.setdefault("FASTMCP_HOST", os.environ.get("MCP_HOST", "0.0.0.0"))
      os.environ.setdefault("FASTMCP_PORT", os.environ.get("MCP_PORT", "8000"))
      mcp.run(transport="streamable-http")

Update docker-compose.yml to accept `MCP_TRANSPORT=streamable-http` (no new service
needed; the env override already propagates).

Update README:
- Add `streamable-http` row to the transport options table.
- Note that `MCP_TRANSPORT=streamable-http` is preferred for new HTTP deployments.
- Update `examples/client_sse.py` to show the streamable-http URL pattern.

Add one test to `tests/test_server.py` that imports `run` and checks the transport
logic does not raise for a mocked `mcp.run` call (patch mcp.run).
```

**Acceptance criteria:**
- [ ] `MCP_TRANSPORT=streamable-http uv run document-xml-mcp` starts without error.
- [ ] Test for the new branch passes.
- [ ] Coverage stays at 100%.

---

### Milestone 17 — Sample clients

**Status: In Progress (examples/ directory created; client_stdio.py and client_sse.py
verified against live server and real DOCX fixture).**

#### Task 17.1 — Stdio sample client (COMPLETE ✓)

`examples/client_stdio.py` — spawns the server as a subprocess, exercises all four
tools, prints structured output. Verified with `input/CV_Test_1.docx`.

#### Task 17.2 — SSE sample client (COMPLETE ✓)

`examples/client_sse.py` — connects to a running SSE server by URL (default
`http://localhost:8000/sse`), calls `list_supported_document_types` and
`parse_document_to_xml`. Works with Docker, docker-compose, self-hosted, or remote.

#### Task 17.3 — Document sample clients in README

**Pre-conditions:**
- Tasks 17.1 and 17.2 complete.

**Prompt:**
```
Add a "Sample Clients" section to README.md between the "Testing with MCP Inspector"
section and "Development Commands".

Content:
1. Brief intro (2 sentences): Python client scripts in examples/ that exercise
   the MCP protocol directly — useful for integration testing, CI smoke tests,
   and as a starting point for custom automation.

2. Subsection: stdio client
   - When to use: local server, scripting, CI
   - Run: `uv run python examples/client_stdio.py --docx input/CV_Test_1.docx`
   - Expected output snippet (4-6 lines)

3. Subsection: SSE client
   - When to use: Docker, remote, n8n integration
   - Start server: `MCP_TRANSPORT=sse uv run document-xml-mcp` or Docker compose
   - Run: `uv run python examples/client_sse.py --url http://localhost:8000/sse --docx input/CV_Test_1.docx`

4. Note on parse_file_to_xml and parse_batch_to_xml: these require the file to exist
   on the server's filesystem; the base64 tool is the right choice for remote use.
```

**Acceptance criteria:**
- [ ] README section is accurate and runnable as documented.
- [ ] No dead links.

---

### Milestone 18 — AGENTS.md consistency fix

**Pre-conditions:**
- Phase 1 complete.

**Context:**
`AGENTS.md` states: "MCP tools must never raise unhandled exceptions to the caller.
Wrap the entire tool body in try/except, return errors as `warnings: [str(exc)]`."

Current `server.py` re-raises all exceptions (the `except Exception` block logs and
re-raises). `test_mcp_tools.py` asserts `pytest.raises(...)` for error cases.

Re-raising is valid MCP behaviour — the framework converts it to an MCP error
response. Returning errors as `warnings` would require all callers to check warnings
rather than catching exceptions, which is less idiomatic.

**Decision needed:** align AGENTS.md with the code (document "re-raise is intentional")
or change the code to return structured warnings.

**Prompt:**
```
Update `AGENTS.md` section "Error Handling at Tool Boundaries" to reflect the actual
implementation:

Replace:
  "MCP tools must never raise unhandled exceptions to the caller.
   Wrap the entire tool body in try/except, return errors as warnings: [str(exc)]."

With:
  "MCP tools catch all internal exceptions, log them at WARNING with exc_info=True,
   and re-raise. The MCP framework converts uncaught exceptions to structured MCP
   error responses — callers receive an error object, not a silent empty response.
   Never swallow exceptions silently. Do not return errors inside a successful
   response dict — use raises."

No code changes. Verify the existing `test_mcp_tools.py` error-case tests still pass.
```

**Acceptance criteria:**
- [ ] AGENTS.md updated.
- [ ] All tests pass.

---

## Phase 2 — Definition of Done

- [ ] All Phase 2 tasks implemented, committed, and CI-green
- [ ] Test count >= 110, coverage 100%
- [ ] `uv run pytest -m "not integration"` passes in < 5 seconds
- [ ] `uv run pytest -m integration` passes on a machine with `uv` and Docker
- [ ] `examples/client_stdio.py --docx input/CV_Test_1.docx` runs end-to-end
- [ ] `examples/client_sse.py` connects to a live SSE server successfully
- [ ] README sample client section is accurate
- [ ] docker-compose.yml healthcheck bug fixed
- [ ] AGENTS.md error-handling section is consistent with code
