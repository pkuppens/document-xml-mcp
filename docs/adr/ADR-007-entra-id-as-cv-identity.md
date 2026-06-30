# ADR-007: Entra ID as CV Identity

**Status:** Accepted
**Date:** 2026-06-30

---

## Context

Parsed CvRecords need a stable, unique identifier so they can be stored, retrieved as MCP Resources (`cv://cvs/{id}`), and correlated with the people they describe. The managed population is approximately 60–100 users, all members of an organisation already tracked in Microsoft Entra (formerly Azure AD).

Three candidate identity schemes were considered:

**A — Server-generated UUID.** On `store_cv`, the server assigns a UUID. Simple, no external dependency. Requires a separate mapping table to correlate a UUID with the person it belongs to.

**B — Entra ID.** The CV is keyed by the user's Entra object ID. A separate Entra MCP server exposes user records (Entra ID, first name, last name); matching a parsed CV to a user is done programmatically or LLM-assisted before calling `store_cv`.

**C — Content-derived hash.** Deterministic from the CvRecord content. Changes when the record changes, making history lookup by ID unreliable.

---

## Decision

**Option B — Entra ID as the CV key.**

`store_cv(entra_id, cv_record)` takes the Entra ID explicitly. The current CvRecord is retrievable at `cv://cvs/{entra_id}`. History is retained server-side as an audit trail; `store_cv` with the same Entra ID replaces the current record and archives the previous one.

---

## Rationale

- **Single source of truth for identity.** Entra is already the authoritative identity store for the organisation. Keying CVs by Entra ID means no separate User table is needed in the CV backing store — the identifier is borrowed from the existing system of record.
- **No mapping table.** A UUID would require storing and maintaining a UUID→Person mapping. Entra ID eliminates this indirection: the CV URI and the person are the same concept.
- **Enables cross-server correlation.** The Entra MCP server and this server share the same key space. A client or LLM can join data from both servers without any translation.
- **One CV per person.** The organisation manages one current CV per employee. Entra ID as key enforces this naturally — a second `store_cv` for the same Entra ID is always an update, never a duplicate.
- **Scale.** At 60–100 users, listing all managed CVs (`cv://cvs/`) fits comfortably in a single LLM context window.

The cost of this decision is a dependency on the Entra MCP server for CV–User matching before storage. This is acceptable: matching is a one-time step in the human-reviewed pipeline, and the Entra server is already a planned dependency.

---

## Consequences

1. `store_cv(entra_id: str, cv_record: dict) → None` is the signature. Entra ID is a required parameter; the server does not generate or infer it.
2. Current CvRecord accessible as MCP Resource at `cv://cvs/{entra_id}` (MIME type: `application/json`).
3. Previous versions are retained as audit trail; no browsable history Resource is exposed to clients.
4. CV–User matching (connecting a parsed CvRecord to an Entra ID) is a client responsibility, optionally LLM-assisted using the Entra MCP server's user list Resource.
5. If the organisation migrates away from Entra, the CV keys remain valid as opaque strings — only the matching step changes.

---

## Review Trigger

Revisit if:
- The managed population grows to include contractors or external parties not in Entra
- A user needs more than one current CV variant (e.g. domain-specific tailorings) — at that point, the key would need to become `{entra_id}/{variant}`
