# ADR-002: MCP Prompt Ownership — Server vs Client

**Status:** Accepted
**Date:** 2026-06-18
**Issue:** [#21](https://github.com/pkuppens/document-xml-mcp/issues/21)

---

## Context

MCP servers can expose **Prompt templates** via `@mcp.prompt()`. The server returns a parameterized list of `PromptMessage` objects; the LLM client applies them. This is different from a client hard-coding the same prompt string locally.

The question arises: for the CV use case, which prompt templates belong in the MCP server, and which should live in the client application?

### How MCP Prompts Work at Runtime

1. Client calls `prompts/list` → server returns available prompt names + argument schemas
2. Client calls `prompts/get(name, arguments)` → server returns populated `PromptMessage[]`
3. Client sends those messages to the LLM → LLM produces output
4. The server is not involved in step 3. It only provides the template.

This means:
- Server prompts are **discoverable** (any client can list them)
- Server prompts are **centrally versioned** (change once, all clients get the update)
- Server prompts are **decoupled from client code** (client doesn't need to know the prompt text)

---

## Decision Rule

Put a prompt in the MCP server if ALL of the following are true:

1. **Reusable across clients** — multiple clients (Claude Desktop, n8n, custom scripts) would benefit from the same template, and maintaining separate copies would create drift
2. **Operates on data this server produces** — the prompt's `cv_xml` parameter is the output of `parse_document_to_xml`; the server "understands" its own output format
3. **No client-specific context required** — the prompt doesn't need access to client-side state (user session, UI preferences, client-specific DB records) that the server cannot know
4. **Not a one-off** — if a prompt is used only once in one client and is tightly coupled to that client's UX, keep it in the client

Keep a prompt in the client if ANY of the following is true:
- It requires client-side credentials or session state
- It is so tightly coupled to a specific UI flow that sharing it would be misleading
- It is experimental and not yet stable enough to version

---

## Classification of CV Prompts

### `analyze_cv_gaps(cv_xml, job_description)`
**Decision: Server** ✓

- Reusable: yes — any client doing CV matching needs this
- Operates on server output: yes — `cv_xml` is this server's product
- No client-specific context: the prompt is parameterized; client supplies both inputs
- Not one-off: core to the CV intelligence use case

### `write_motivation_letter(cv_xml, assignment, tone)`
**Decision: Server** ✓

- Reusable: yes — multiple clients (n8n workflow, Claude Desktop, API script) will write letters
- Operates on server output: yes — `cv_xml` is this server's product
- No client-specific context: `tone` is a parameter, not client state
- Not one-off: central to the repeatable CV pipeline

### `rewrite_cv_for_assignment(cv_xml, assignment, target_format)`
**Decision: Server** ✓

- Reusable: yes — same rationale as above
- Operates on server output: yes
- No client-specific context: all inputs are parameters
- Not one-off: core workflow step

### `answer_cv_questions(cv_xml, question)`
**Decision: Server** ✓

- Reusable: yes — any client doing interactive Q&A over a CV needs this
- Operates on server output: yes
- No client-specific context: fully parameterized
- Not one-off: enables interactive CV exploration

All four prompts pass the decision rule. They belong in the server.

---

## Consequences

1. All four prompts will be implemented as `@mcp.prompt()` decorated functions in `src/xml_processing_mcp/server.py`, importing from `src/xml_processing_mcp/prompts/`.
2. Prompt implementations live in `src/xml_processing_mcp/prompts/cv_analysis.py` and `src/xml_processing_mcp/prompts/cv_generation.py`.
3. Any MCP client connecting to this server can discover and use these prompts without client-side prompt engineering.
4. Prompt text is versioned with the server — clients get updates on server upgrade.
5. If a client needs a significantly different version of a prompt, it can override locally. Server prompts are defaults, not mandates.

---

## Review Trigger

Revisit if:
- A prompt requires client-side credentials or session data that cannot be passed as a parameter
- A client needs a fundamentally different version for its specific UX
- The prompt volume grows large enough to warrant a dedicated prompts server
