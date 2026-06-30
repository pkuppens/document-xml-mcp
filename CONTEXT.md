# Domain Context — document-xml-mcp

MCP primitives (Tool, Prompt, Resource, Source, Sink, DocumentNode, DocumentParser, DocumentRenderer) and pipeline abstractions are defined in [docs/glossary.md](docs/glossary.md). This file defines **domain terms** only — concepts specific to the CV intelligence use case.

---

## CV (Curriculum Vitae)

A structured document describing a person's professional background. In this project, a CV is the primary input artifact: it arrives as a DOCX file (or base64-encoded DOCX) and is processed into XML and then into a **CvRecord**.

---

## CvRecord

The canonical, unified JSON representation of a CV, produced by `extract_cv_fields`. Contains **core fields** (always attempted) and **extended fields** (any additional sections found in the source document).

**Core fields:** `name`, `contact`, `summary`, `skills`, `experience`, `education`, `languages`, `certifications`, `warnings`

**Extended fields:** any section heading not in the core set is normalised to a snake_case key and merged into the top-level JSON object alongside the core fields. Word export templates ignore unknown keys; LLM prompts can use any key.

---

## Core Field

A named field in a CvRecord that the extraction pipeline always attempts to populate. Defined by `_SECTION_KEYWORDS` in `cv_field_extractor.py`. Missing core fields produce a warning; they are never omitted from the output.

---

## Extended Field

A field in a CvRecord derived from a CV section whose heading does not match any core field keyword. The section heading is normalised to snake_case and used as the JSON key. Value is a list of text items collected from that section. Extended fields are invisible to Word templates but available to LLM prompts.

---

## Knowledge Area Taxonomy

A two-level controlled vocabulary for classifying skills and technologies.

- **Domain** (level 1): broad category, e.g. "Programming", "Databases", "DevOps", "Cloud"
- **Skill** (level 2): specific term within one or more domains, e.g. "Python" under "Programming"; "Azure" under "DevOps", "Cloud", and "Databases"

A Skill may belong to multiple Domains (many-to-many). The taxonomy is the authoritative source for canonical skill names used when normalising CvRecord `skills` lists.

**Governance:** Human-reviewed. The server flags unrecognised skills as **Skill Candidates** during extraction. A human reviews candidates and promotes them (or maps them as aliases) to the taxonomy. The server never modifies the taxonomy autonomously.

---

**Storage:** Initially a static JSON/YAML file bundled with the server, exposed as a MCP Resource (`cv://knowledge-areas/taxonomy`). The implementation must sit behind a `TaxonomyStore` abstraction so the backing store can be swapped to a database without touching extraction logic. Migration to database storage is anticipated.

---

## Personality Trait Vocabulary

A controlled list of personality traits used to ensure consistent language in generated output (motivation letters, candidate profiles). Exposed as a MCP Resource (`cv://knowledge-areas/personality-traits`).

Each entry contains:
- **name** — canonical trait label (e.g. "Analytical", "Proactive")
- **definition** — clear description of what the trait means in a professional context
- **trigger_words** — terms and phrases that signal this trait in CV text; used by the LLM to select applicable traits during generation

Traits are not extracted automatically into the CvRecord. They are reference context the LLM reads when producing output. Manual additions and edits are possible via a UI (client/admin concern). Storage follows the same migration path as the Knowledge Area Taxonomy: static file initially, database when UI-driven editing is needed.

---

## Skill Candidate

A skill term found in a CvRecord that does not match any entry in the Knowledge Area Taxonomy. Surfaced in the `skill_candidates` field of the CvRecord output. Awaits human review before promotion to the taxonomy.

---

## CV Pipeline

The sequence of steps from raw document to stored CV:

1. `parse_document_to_xml` — DOCX bytes → clean XML
2. `extract_cv_fields` — XML → CvRecord (pure computation, no side effects)
3. **Review** — human inspects and corrects the CvRecord before storage
4. `store_cv` — approved CvRecord → Managed CV with assigned ID

Steps 1–2 are server-side tools. Step 3 is a client/human responsibility, optionally LLM-assisted via two server prompts:

- `review_cv_completeness(cv_record_json)` — checks completeness (core fields populated, no obvious gaps) and taxonomy alignment (skills normalised against the Knowledge Area Taxonomy). Small prompt; no XML required.
- `review_cv_accuracy(cv_xml, cv_record_json)` — cross-checks extracted fields against the source XML to catch mis-parsed or missing content. Large prompt; requires both XML and CvRecord.

The human decides whether to accept LLM suggestions before calling `store_cv`. Step 4 is an explicit tool call; it is never triggered automatically.

---

## User

A person whose CV is managed by this system. Identified by their **Entra ID** (Microsoft Entra, formerly Azure AD). First name, last name, and Entra ID are provided by a dedicated Entra MCP server (separate from this one). The managed population is approximately 60–100 users.

---

## Managed CV

A CvRecord that has been stored in the backing store and linked to a **User** via Entra ID. Retrievable as a MCP Resource at `cv://cvs/{entra_id}` (or `cv://cvs/{entra_id}/{version}` — see CV Versioning). The stored artifact is the CvRecord JSON — the intermediate XML is not persisted. Other formats (Word, PDF) are derived from the CvRecord via templates when needed.

**CV–User matching:** connecting a parsed CvRecord to an Entra User (by name or other signals) can be done programmatically or via LLM prompt. The Entra MCP server exposes the user list as a Resource; at 60–100 users it fits comfortably in a single LLM context window.

**Versioning:** one current CV per User at all times. `store_cv` replaces the current record; the previous version is retained as an **audit trail** (recovery safety net, not browsable by clients). Current CV: `cv://cvs/{entra_id}`. History is accessible to administrators only; there is no listing Resource for historical versions. A `restore_cv(entra_id, timestamp)` tool may be added if recovery workflows are needed.
