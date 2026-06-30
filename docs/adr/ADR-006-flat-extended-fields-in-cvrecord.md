# ADR-006: Flat Extended Fields in CvRecord

**Status:** Accepted
**Date:** 2026-06-30

---

## Context

`extract_cv_fields` extracts a CvRecord from CV XML. The extraction handles a fixed set of **core fields** (name, contact, summary, skills, experience, education, languages, certifications). Real CVs contain additional sections beyond this set: hobbies, personal projects, volunteer work, publications, side projects, and others that vary per candidate.

Two structural options for representing these additional sections in the CvRecord JSON:

**Option A — Wrapper object:**
```json
{
  "skills": ["Python", "Azure"],
  "extra_sections": {
    "hobbies": ["cycling", "open source"],
    "personal_projects": ["built a CV parser"]
  }
}
```

**Option B — Flat top-level keys:**
```json
{
  "skills": ["Python", "Azure"],
  "hobbies": ["cycling", "open source"],
  "personal_projects": ["built a CV parser"]
}
```

Unknown section headings are normalised to snake_case before use as JSON keys (e.g. "Personal Projects" → `personal_projects`).

---

## Decision

**Option B — flat top-level keys.**

Extended fields are merged directly into the CvRecord JSON at the top level alongside core fields. Section headings are normalised to snake_case. On key collision, content is appended (never dropped, never silently overwritten).

---

## Rationale

- **LLM prompts** (motivation letter, gap analysis) take the full CvRecord as input. Flat structure means the LLM reads hobbies, projects, and other signals without navigating a wrapper — any field is equally accessible.
- **Word export templates** iterate only over keys they know about; unknown top-level keys are silently skipped. A wrapper adds no value here — the template already ignores `extra_sections.hobbies` and `hobbies` equally.
- **Prevent data loss.** The governing principle is: never discard CV content. Flat merging with append-on-collision satisfies this with minimal complexity.
- The wrapper option adds one level of nesting that benefits no downstream consumer and would need to be unwrapped in every prompt that wants to use the data.

---

## Consequences

1. `extract_cv_fields` appends unrecognised sections to the CvRecord at the top level.
2. Section headings are normalised: lowercased, non-alphanumeric characters replaced with underscores, consecutive underscores collapsed, leading/trailing underscores stripped.
3. On key collision (two sections normalise to the same key, or an extended field collides with a core field name), content lists are merged — no data is dropped.
4. Clients that iterate over CvRecord keys must handle unexpected keys gracefully (Word templates already do; LLM prompts benefit from seeing them).
5. The CvRecord JSON schema is open-ended by design: the set of possible keys is not fixed.

---

## Review Trigger

Revisit if:
- A downstream system requires a strict closed schema and cannot tolerate unknown keys
- Key normalisation causes collisions frequent enough to obscure meaning
