# ADR-005: CV Intelligence vs Document Processing — One Server or Two?

**Status:** Accepted
**Date:** 2026-06-18
**Issue:** [#24](https://github.com/pkuppens/document-xml-mcp/issues/24)

---

## Context

This MCP server was designed as a **document processing server**: it converts DOCX bytes to clean, structured XML. The proposed CV use case introduces a second category of functionality:

**CV intelligence** — domain-specific operations on parsed CV XML:
- Analyzing skill gaps vs a job description
- Writing motivation letters
- Rewriting a CV for a specific assignment
- Answering questions about a CV
- Extracting structured fields (name, skills, experience) from CV XML

These raise the question: should CV intelligence live in this server, or in a separate `cv-intelligence-mcp` server?

### What MCP Supports

An MCP client can connect to **multiple servers simultaneously**. Claude Desktop, n8n, and custom clients all support multi-server configurations. A two-server setup is not harder for clients — it is a first-class MCP pattern.

### Operations to Classify

| Operation | Category | Notes |
|-----------|----------|-------|
| `parse_document_to_xml` | Document processing | Existing, format-agnostic |
| `parse_file_to_xml` | Document processing | Existing, format-agnostic |
| `parse_batch_to_xml` | Document processing | Existing, format-agnostic |
| `extract_cv_fields(xml)` | CV intelligence | Parses CV structure from XML |
| `analyze_cv_gaps` prompt | CV intelligence | LLM instruction, CV-domain |
| `write_motivation_letter` prompt | CV intelligence | LLM instruction, CV-domain |
| `rewrite_cv_for_assignment` prompt | CV intelligence | LLM instruction, CV-domain |
| `answer_cv_questions` prompt | CV intelligence | LLM instruction, generic Q&A |
| `cv://templates/export-schema` resource | CV intelligence | CV-specific reference data |
| `cv://templates/assignment-format` resource | CV intelligence | CV-specific reference data |

---

## Options Considered

### Option A: One Server (extend this server)

Add CV intelligence operations (prompts, resources, tools) directly to `src/xml_processing_mcp/server.py`, organized in subdirectories (`prompts/`, `resources/`).

**Pros:**
- One deployment unit; simpler local dev and Docker setup
- Clients need one connection, not two
- Good for learning: all MCP primitives in one place
- Low overhead for a portfolio/learning project

**Cons:**
- Server no longer has a single clear responsibility
- A generic DOCX-to-XML client gets CV-specific prompts it doesn't need
- Growing toward a "CV tool server" rather than a "document processing server"
- Harder to extract later when the intelligence grows

### Option B: Two Servers

Keep this server pure document processing. Create a new `cv-intelligence-mcp` server (separate repo or package) for CV-domain operations.

**Pros:**
- Each server has one clear responsibility
- Document processing server is reusable for non-CV use cases (legal docs, reports)
- CV intelligence can evolve independently (different dependencies, deployment)
- Correct long-term architecture

**Cons:**
- Two repos/packages to maintain
- Two processes to run locally
- More setup for first-time users
- Premature for a learning project where the CV intelligence is still being defined

---

## Decision

**Option A: One server, with clear internal module separation.**

For this project's current phase (learning + portfolio), the pragmatic choice is a single server. The CV intelligence operations are organized in distinct subdirectories (`prompts/`, `resources/`) with no coupling to the core document pipeline (`parsers/`, `renderers/`, `sources/`, `sinks/`). This keeps the architecture extractable later without paying the two-repo overhead now.

The exception is `extract_cv_fields` (a Tool): it uses `lxml`, which is already a dependency, and is pure computation with no CV-domain opinions — it is closer to document processing than intelligence. It belongs in this server.

### Boundary Rule (for this server)

**In scope:**
- Any operation that converts, parses, or structurally normalizes documents (format-agnostic or CV-specific)
- Prompt templates that operate on XML content this server produces
- Resources that define the structure of documents this server handles
- Pure computation tools with no LLM calls and no external side effects

**Out of scope:**
- LLM calls inside tools (anti-pattern — use Prompts)
- Persistence operations (database writes, cloud storage) — see ADR-004
- Matching/scoring algorithms against external data sources
- Any operation that requires credentials or access to external systems

---

## Consequences

1. `src/xml_processing_mcp/server.py` will register tools, prompts, and resources from separate modules.
2. `src/xml_processing_mcp/prompts/` and `src/xml_processing_mcp/resources/` are new directories — they contain CV-domain logic but remain cleanly separated from the document pipeline.
3. If a second server is needed in the future, the extraction path is clear: move `prompts/` and `resources/` to a new repo, update `server.py`.
4. A future `cv-intelligence-mcp` server can call this server's tools (chaining) or operate on pre-processed XML directly.

---

## Review Trigger

Revisit this decision when:
- A non-CV use case needs the document processing server and is confused by CV-specific prompts/resources
- The CV intelligence grows to require external API dependencies (LLM providers, job boards, databases)
- A second team or project needs to consume just the document processing functionality
