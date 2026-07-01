# ADR-008: Human-Gated Knowledge Area Taxonomy Growth

**Status:** Accepted
**Date:** 2026-06-30

---

## Context

The Knowledge Area Taxonomy is a two-level controlled vocabulary (Domain → Skill) used to normalise skill terms in CvRecords to canonical names, and to provide consistent reference context for LLM prompts. New CVs will contain skill terms not yet in the taxonomy. The taxonomy must grow over time.

Three growth strategies were considered:

**A — Automatic.** Any unrecognised skill term is immediately added as a new Taxonomy entry. No human involvement required.

**B — Human-gated.** Unrecognised skill terms are surfaced as **Skill Candidates** in the CvRecord output. A human reviews candidates and either promotes them to the taxonomy (with canonical name, domain assignment, and optional aliases) or maps them to an existing entry. The taxonomy is never modified automatically.

**C — LLM-assisted curation.** During extraction, an LLM prompt suggests a canonical mapping for each unrecognised term ("Python 3.11" → "Python"); a human reviews only low-confidence suggestions.

---

## Decision

**Option B — Human-gated growth.**

Unrecognised skills are surfaced in a `skill_candidates` field in the CvRecord. The extraction pipeline and the taxonomy are decoupled: extraction always completes, taxonomy updates are a separate administrative act.

---

## Rationale

The taxonomy's value is **precision**: "Python", "Python 3", "Python 3.x", "Python 3.11", and "Python (advanced)" are five surface forms of the same canonical skill. Automatic growth (Option A) would add all five as separate entries, defeating normalisation. The taxonomy becomes useful only if it maps variants to a single canonical name — a judgment that requires human context.

Option C (LLM-assisted) produces higher quality than A but adds an LLM call to the extraction path, coupling CV parsing to LLM availability and latency. It also wraps an LLM call inside a Tool, which is an explicit anti-pattern in this codebase (see ADR-002). The suggestion step could be a Prompt instead, but that makes it a client-side workflow — equivalent to Option B with an LLM in the review loop, which the client can add without server involvement.

Human review is acceptable in this workflow: the pipeline already includes a human review step between extraction and storage (see CONTEXT.md — CV Pipeline). Taxonomy curation fits naturally alongside that review.

---

## Consequences

1. `extract_cv_fields` populates a `skill_candidates` field in the CvRecord listing any skill terms not matched in the taxonomy.
2. The taxonomy is stored behind a `TaxonomyStore` abstraction. Initial implementation: a static JSON file bundled with the server, exposed as MCP Resource `cv://knowledge-areas/taxonomy`. Migration to a database-backed store is anticipated without changes to extraction logic.
3. No server tool adds entries to the taxonomy. Taxonomy updates are applied externally (file edit + redeploy for static store; admin API or UI for database store).
4. Skills in CvRecords are normalised against the taxonomy at extraction time. Unmatched terms are preserved as-is in the `skills` field and also listed in `skill_candidates`.
5. When a Skill Candidate is promoted (human adds it to the taxonomy with a canonical name), previously extracted CvRecords are not retroactively updated — only future extractions reflect the new entry. If retroactive normalisation is needed, `extract_cv_fields` must be re-run against the stored XML. *(Note: stored XML is not retained — see ADR-007. Re-normalisation requires re-importing the original DOCX.)*

---

## Review Trigger

Revisit if:
- Skill Candidate volume grows large enough that manual review becomes a bottleneck (trigger: more than ~20 new candidates per week sustained)
- An LLM-assisted curation prompt is added client-side — at that point Option C becomes available without server changes
