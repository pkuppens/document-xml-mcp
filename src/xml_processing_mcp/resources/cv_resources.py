"""CV resource handlers — load and serve static template files."""

from pathlib import Path

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def get_cv_export_schema() -> str:
    """Return the CV XML export schema as a string.

    Clients read this resource (cv://templates/export-schema) to understand
    the target XML structure produced by parse_document_to_xml for CV documents.
    """
    return (_TEMPLATES_DIR / "cv_export_schema.xml").read_text(encoding="utf-8")


def get_assignment_format() -> str:
    """Return the assignment description format template as a string.

    Clients read this resource (cv://templates/assignment-format) to understand
    what fields and structure are expected when providing a job description to
    the analyze_cv_gaps or write_motivation_letter prompts.
    """
    return (_TEMPLATES_DIR / "assignment_format.md").read_text(encoding="utf-8")
