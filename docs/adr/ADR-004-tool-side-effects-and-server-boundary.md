# ADR-004: Tool Side-Effects and MCP Server Boundary

**Status:** Partially Superseded
**Date:** 2026-06-18
**Issue:** [#23](https://github.com/pkuppens/document-xml-mcp/issues/23)
**Superseded in part by:** ADR-006 (CvRecord schema), ADR-007 (Entra ID as CV identity), ADR-008 (taxonomy governance)

**What changed:** CV persistence (`store_cv` keyed by Entra ID) and Knowledge Area Taxonomy management are now in-scope for this server. The "no external service dependencies" rule is relaxed for these two backing stores. The `store_cv` classification below is overridden — see ADR-007. All other decisions (no webhook, no assignment search, no LLM calls inside tools) remain in force.

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

## Server's Responsibility

> **This server converts documents to structured XML, extracts structured CV data, and manages the CV backing store for a known set of users.**

Allowed side effects:
- Writing XML output to its own configured filesystem paths (existing `FileSink` pattern)
- Reading and writing to the CV backing store (CvRecord storage keyed by Entra ID)
- Reading and writing to the Knowledge Area Taxonomy store (`TaxonomyStore` abstraction)
- Logging

---

## Decision Rule for Side-Effecting Operations

A side-effecting operation belongs in **this server** only if:
1. It writes to a resource this server already owns (its configured filesystem)
2. It does not introduce new external service dependencies (databases, APIs, message queues)
3. It is a natural completion of an existing tool's operation (not a new capability)
4. It does not require new credentials or authentication scope — any operation that introduces API keys, OAuth tokens, or connection strings belongs in a dedicated server that owns and isolates that credential

Otherwise, the operation belongs in:
- **The client** — if it uses client-owned infrastructure (the client's database, the client's storage)
- **A separate MCP server** — if it is reusable across clients but out of scope here (e.g., a `cv-persistence-mcp` server)

---

## Classification of Candidate Operations

### `store_cv(entra_id, cv_record)` — write CvRecord to backing store
**Decision: In this server** ✓ *(original decision reversed — see ADR-007)*

CV persistence is now in scope. The server owns a backing store for CvRecords keyed by Entra ID, with audit-trail history. Extraction (`extract_cv_fields`) remains pure; storage is an explicit separate tool call made only after human review. See ADR-007 for the full rationale.

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

1. `store_cv` WILL be implemented as a Tool in this server (explicit, after human review, keyed by Entra ID). *(Original decision reversed — see ADR-007.)*
2. A `TaxonomyStore` abstraction WILL be added for Knowledge Area Taxonomy management. *(See ADR-008.)*
3. `send_to_n8n_webhook`, `search_assignments` will NOT be implemented as Tools in this server.
4. `extract_cv_fields` WILL be implemented as a Tool here (pure computation, no side effects).
5. `score_cv_vs_job` WILL be implemented as a Prompt, not a Tool.
6. The n8n integration pattern (n8n calls this server, then handles routing) remains the reference integration pattern.

---

## Review Trigger

Revisit if:
- A strongly reusable, stateless side-effecting operation emerges that naturally belongs alongside document processing
- A `cv-persistence-mcp` server is built — at that point, `DatabaseSink` could be a client of that server rather than code in this repo
