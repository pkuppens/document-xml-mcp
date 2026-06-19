# ADR-004: Tool Side-Effects and MCP Server Boundary

**Status:** Accepted
**Date:** 2026-06-18
**Issue:** [#23](https://github.com/pkuppens/document-xml-mcp/issues/23)

---

## Context

MCP Tools can have side effects: write to a database, call an external API, send a webhook. The question is not whether a Tool *can* have side effects — it can — but whether a specific side-effecting operation belongs in **this server**.

The current server has one side-effecting pattern: `FileSink`, used by `parse_batch_to_xml` to write processed XML to the server's filesystem. This is acceptable because:
- The server's filesystem is within its operational boundary (configured via allow-lists)
- Batch output is the natural end-state of the batch tool's operation
- No external service dependencies are introduced

Proposed new operations with side effects:
- `store_cv(cv_id, xml, metadata)` — write to a database
- `send_to_n8n_webhook(xml, webhook_url)` — HTTP POST to n8n
- `search_assignments(query)` — query an external job database
- `score_cv_vs_job(cv_xml, job_xml)` — LLM-based scoring

---

## Server's Single Responsibility

> **This server converts documents to structured XML. It does not own, manage, or persist application data.**

Everything else is out of scope. The server's allowed side effects are:
- Writing XML output to its own configured filesystem paths (existing `FileSink` pattern)
- Logging

---

## Decision Rule for Side-Effecting Operations

A side-effecting operation belongs in **this server** only if:
1. It writes to a resource this server already owns (its configured filesystem)
2. It does not introduce new external service dependencies (databases, APIs, message queues)
3. It is a natural completion of an existing tool's operation (not a new capability)

Otherwise, the operation belongs in:
- **The client** — if it uses client-owned infrastructure (the client's database, the client's storage)
- **A separate MCP server** — if it is reusable across clients but out of scope here (e.g., a `cv-persistence-mcp` server)

---

## Classification of Candidate Operations

### `store_cv(cv_id, xml, metadata)` — write to database
**Decision: Client-owned or separate server**

This server does not own a database. Introducing a database dependency would:
- Require configuring credentials (connection strings, auth tokens) in this server
- Couple document processing to a specific storage technology
- Violate the single-responsibility boundary

Different clients store differently: one uses PostgreSQL, another uses MongoDB, another writes to S3. The server cannot serve all of these without becoming a persistence server — which is a different server.

**Where it belongs:** The client calls `parse_document_to_xml`, receives XML, then stores it using its own persistence layer. Or: a dedicated `cv-persistence-mcp` server wraps the database and exposes `store_cv` as its tool.

**Note on the Sink pattern:** If a `DatabaseSink` were added to this project, it would be an internal pipeline component (not a Tool) — and would still require external credentials. The Sink pattern is appropriate for filesystem writes (owned by this server). It is not appropriate for external services.

### `send_to_n8n_webhook(xml, webhook_url)` — HTTP POST
**Decision: Client-owned**

Sending to a webhook is an integration concern. The client (or n8n itself, as a workflow orchestrator) is the natural owner. The server should not know about downstream consumers.

The existing n8n workflow (`n8n/workflows/parse-document.json`) correctly inverts this: n8n calls the server's tools, receives XML, and then routes it. This is the right direction of dependency.

### `search_assignments(query)` — query external job database
**Decision: Separate server**

A job database is a domain-specific external resource. Querying it belongs in a service that owns that domain. If exposed via MCP, it would be a separate `assignments-mcp` server.

### `score_cv_vs_job(cv_xml, job_xml)` — LLM-based scoring
**Decision: Prompt (not a Tool)**

Any operation that wraps an LLM call inside a Tool is an anti-pattern. The correct primitive is a Prompt: expose the scoring instruction template, and let the client/LLM execute it. See also ADR-002.

### `extract_cv_fields(xml)` — parse XML to structured JSON
**Decision: Tool in this server** ✓

- Pure computation: XML in, JSON out — no LLM, no external services
- Uses `lxml`, already a dependency
- Natural extension of the document processing pipeline
- No external side effects; no credentials needed
- Reusable by any client receiving XML from this server

---

## Consequences

1. `store_cv`, `send_to_n8n_webhook`, `search_assignments` will NOT be implemented as Tools in this server.
2. `DatabaseSink` will NOT be added to this codebase in its current scope.
3. `extract_cv_fields` WILL be implemented as a Tool here (pure computation, no side effects).
4. `score_cv_vs_job` WILL be implemented as a Prompt, not a Tool.
5. Clients that need persistence after receiving XML from this server implement it themselves, or connect to a purpose-built persistence MCP server.
6. The n8n integration pattern (n8n calls this server, then handles routing) remains the reference integration pattern.

---

## Review Trigger

Revisit if:
- A strongly reusable, stateless side-effecting operation emerges that naturally belongs alongside document processing
- A `cv-persistence-mcp` server is built — at that point, `DatabaseSink` could be a client of that server rather than code in this repo
