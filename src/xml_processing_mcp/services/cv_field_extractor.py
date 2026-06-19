"""Extract structured fields from CV XML produced by parse_document_to_xml.

Heuristic extraction: section headings are matched case-insensitively against
known CV section keywords. Text is collected from paragraphs, list items, and
table cells within each matched section.

Section keyword mapping:
  name        → first <heading level="1"> or <heading class="Title">
  contact     → section titled: contact, contactgegevens, personal, persoonlijk
  summary     → section titled: profile, summary, profiel, samenvatting, objective
  skills      → section titled: skills, vaardigheden, competencies, competenties, expertise, technical
  experience  → section titled: experience, ervaring, work, werkervaring, employment, career, carrière
  education   → section titled: education, opleiding, opleidingen, study, studies
  languages   → section titled: languages, talen, language
  certifications → section titled: certifications, certificaten, courses, cursussen, training
"""

import re
from dataclasses import dataclass, field

from lxml import etree

_SECTION_KEYWORDS: dict[str, list[str]] = {
    "contact": ["contact", "contactgegevens", "personal", "persoonlijk", "personal information"],
    "summary": ["profile", "profiel", "summary", "samenvatting", "objective", "about"],
    "skills": ["skills", "vaardigheden", "competencies", "competenties", "expertise", "technical skills"],
    "experience": ["experience", "ervaring", "work experience", "werkervaring", "employment", "career", "carrière"],
    "education": ["education", "opleiding", "opleidingen", "study", "studies", "academic"],
    "languages": ["languages", "talen", "language"],
    "certifications": ["certifications", "certificaten", "courses", "cursussen", "training", "certificates"],
}

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"[\+\(]?[\d\s\-\(\)]{7,15}\d")
_LINKEDIN_RE = re.compile(r"linkedin\.com/in/[\w\-]+", re.IGNORECASE)


@dataclass
class CvContact:
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    location: str | None = None


@dataclass
class CvExperience:
    title: str | None = None
    company: str | None = None
    period: str | None = None
    description: str | None = None


@dataclass
class CvEducation:
    degree: str | None = None
    institution: str | None = None
    year: str | None = None


@dataclass
class CvFields:
    name: str | None = None
    contact: CvContact = field(default_factory=CvContact)
    summary: str | None = None
    skills: list[str] = field(default_factory=list)
    experience: list[CvExperience] = field(default_factory=list)
    education: list[CvEducation] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _all_text(element: etree._Element) -> str:
    """Collect all text content from an element and its descendants."""
    return " ".join(t.strip() for t in element.itertext() if isinstance(t, str) and t.strip())


def _section_key(title: str) -> str | None:
    """Map a section title to a canonical key, or None if unrecognised."""
    lower = title.lower().strip()
    for key, keywords in _SECTION_KEYWORDS.items():
        if any(lower == kw or lower.startswith(kw) for kw in keywords):
            return key
    return None


def _collect_items(section: etree._Element) -> list[str]:
    """Collect all <item> text from list elements within a section."""
    return [_all_text(item) for item in section.findall(".//item") if _all_text(item)]


def _collect_paragraphs(section: etree._Element) -> list[str]:
    return [_all_text(p) for p in section.findall(".//paragraph") if _all_text(p)]


def _table_rows(section: etree._Element) -> list[list[str]]:
    rows = []
    for row in section.findall(".//row"):
        cells = [_all_text(c) for c in row.findall("cell")]
        if any(cells):
            rows.append(cells)
    return rows


def _extract_contact(text: str, contact: CvContact) -> None:
    """Parse contact details from a plain text string using regex."""
    if not contact.email:
        m = _EMAIL_RE.search(text)
        if m:
            contact.email = m.group()
    if not contact.phone:
        m = _PHONE_RE.search(text)
        if m:
            contact.phone = m.group().strip()
    if not contact.linkedin:
        m = _LINKEDIN_RE.search(text)
        if m:
            contact.linkedin = m.group()


def _parse_experience_table(rows: list[list[str]]) -> list[CvExperience]:
    """Heuristically parse a table into experience entries.

    Tries to identify period, role/title, and company from column order.
    Skips header rows (all cells look like column labels).
    """
    if not rows:
        return []

    experiences = []
    for row in rows:
        if len(row) < 2:
            continue
        exp = CvExperience()
        # Guess column roles by content heuristics
        for cell in row:
            lower = cell.lower()
            if re.search(r"\d{4}", cell) and ("–" in cell or "-" in cell or "present" in lower or "heden" in lower):
                exp.period = cell
            elif not exp.title and len(cell) > 3 and not any(c.isdigit() for c in cell[:5]):
                exp.title = cell
            elif exp.title and not exp.company:
                exp.company = cell
            elif exp.company and not exp.description:
                exp.description = cell
        if exp.title or exp.period:
            experiences.append(exp)
    return experiences


def _parse_education_table(rows: list[list[str]]) -> list[CvEducation]:
    if not rows:
        return []
    entries = []
    for row in rows:
        if len(row) < 2:
            continue
        edu = CvEducation()
        for cell in row:
            if re.fullmatch(r"\d{4}", cell.strip()):
                edu.year = cell.strip()
            elif not edu.degree and len(cell) > 3:
                edu.degree = cell
            elif edu.degree and not edu.institution:
                edu.institution = cell
        if edu.degree or edu.year:
            entries.append(edu)
    return entries


def extract_cv_fields(xml: str) -> dict:
    """Parse CV XML into structured fields.

    Parameters
    ----------
    xml:
        Clean CV XML string as produced by parse_document_to_xml.

    Returns
    -------
    dict
        Structured CV fields: name, contact, summary, skills, experience,
        education, languages, certifications, warnings.
    """
    try:
        root = etree.fromstring(xml.encode("utf-8"))
    except etree.XMLSyntaxError as exc:
        raise ValueError(f"Invalid XML: {exc}") from exc

    result = CvFields()
    body_found = root.find(".//body")
    body = body_found if body_found is not None else root

    # Extract name from first heading with level="1" or class="Title"
    for heading in body.iter("heading"):
        lvl = heading.get("level", "")
        cls = heading.get("class", "").lower()
        text = _all_text(heading)
        if text and (lvl == "1" or "title" in cls):
            result.name = text
            break
    if not result.name:
        result.warnings.append("Could not extract candidate name — no level-1 heading found")

    # Walk sections and classify by title
    seen_sections: set[str] = set()
    for section in body.iter("section"):
        title = section.get("title", "").strip()
        key = _section_key(title)
        if key is None:
            continue
        seen_sections.add(key)
        full_text = _all_text(section)

        if key == "contact":
            _extract_contact(full_text, result.contact)

        elif key == "summary":
            paragraphs = _collect_paragraphs(section)
            result.summary = " ".join(paragraphs) if paragraphs else full_text or None

        elif key == "skills":
            items = _collect_items(section)
            if items:
                result.skills = items
            else:
                # Fall back: split paragraphs on common delimiters
                paragraphs = _collect_paragraphs(section)
                for para in paragraphs:
                    result.skills.extend(s.strip() for s in re.split(r"[,;|]", para) if s.strip())

        elif key == "experience":
            rows = _table_rows(section)
            if rows:
                result.experience = _parse_experience_table(rows)
            else:
                items = _collect_items(section)
                paragraphs = _collect_paragraphs(section)
                for text in items + paragraphs:
                    result.experience.append(CvExperience(description=text))

        elif key == "education":
            rows = _table_rows(section)
            if rows:
                result.education = _parse_education_table(rows)
            else:
                items = _collect_items(section)
                paragraphs = _collect_paragraphs(section)
                for text in items + paragraphs:
                    result.education.append(CvEducation(degree=text))

        elif key == "languages":
            result.languages = _collect_items(section) or re.split(r"[,;|]", _all_text(section))

        elif key == "certifications":
            result.certifications = _collect_items(section) or _collect_paragraphs(section)

    # Warn for missing expected sections
    for key in ("skills", "experience"):
        if key not in seen_sections:
            result.warnings.append(f"Section '{key}' not found in CV — may be missing or use an unrecognised heading")

    # Also scan all text for contact info if not yet found from a contact section
    if not result.contact.email or not result.contact.phone:
        _extract_contact(_all_text(body), result.contact)

    return {
        "name": result.name,
        "contact": {
            "email": result.contact.email,
            "phone": result.contact.phone,
            "linkedin": result.contact.linkedin,
            "location": result.contact.location,
        },
        "summary": result.summary,
        "skills": result.skills,
        "experience": [
            {
                "title": e.title,
                "company": e.company,
                "period": e.period,
                "description": e.description,
            }
            for e in result.experience
        ],
        "education": [
            {
                "degree": e.degree,
                "institution": e.institution,
                "year": e.year,
            }
            for e in result.education
        ],
        "languages": result.languages,
        "certifications": result.certifications,
        "warnings": result.warnings,
    }
