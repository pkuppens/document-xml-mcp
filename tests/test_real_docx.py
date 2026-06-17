"""Real-file regression tests using input/CV_Test_1.docx.

These tests are marked with ``@pytest.mark.real_file`` so they can be run
selectively::

    uv run pytest -m real_file          # run only real-file tests
    uv run pytest -m "not real_file"    # skip real-file tests

Task 12.1 — smoke test: verifies that processing the real DOCX succeeds and
returns plausible results.

Task 12.2 — golden-file snapshot: on the first run the rendered XML is written
to ``tests/fixtures/CV_Test_1_golden.xml``; on subsequent runs the output is
compared character-for-character against that stored snapshot.
"""

from pathlib import Path

import pytest

from xml_processing_mcp.config import Settings
from xml_processing_mcp.services.document_processing_service import DocumentProcessingService
from xml_processing_mcp.sources.bytes_source import BytesSource

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INPUT_DOCX = Path(__file__).parent.parent / "input" / "CV_Test_1.docx"
_GOLDEN_XML = Path(__file__).parent / "fixtures" / "CV_Test_1_golden.xml"

# Skip the entire module when the fixture file is absent (e.g. in CI).
# The file is gitignored and must be provided manually for local runs.
pytestmark = pytest.mark.skipif(
    not _INPUT_DOCX.exists(),
    reason=f"Fixture file not found: {_INPUT_DOCX}",
)


def _service() -> DocumentProcessingService:
    return DocumentProcessingService(Settings())


# ---------------------------------------------------------------------------
# Task 12.1 — smoke test
# ---------------------------------------------------------------------------


@pytest.mark.real_file
def test_real_cv_smoke() -> None:
    """Processing CV_Test_1.docx must succeed with no warnings and valid XML."""
    data = _INPUT_DOCX.read_bytes()
    src = BytesSource(data)
    resp = _service().process(src, "CV_Test_1.docx")

    assert resp.warnings == [], f"unexpected warnings: {resp.warnings}"
    assert resp.stats.paragraph_count > 0, "expected at least one paragraph in the CV"
    assert resp.stats.table_count >= 0, "table_count must be non-negative"
    assert "<document" in resp.xml, "rendered XML must contain a <document element"


# ---------------------------------------------------------------------------
# Task 12.2 — golden-file snapshot
# ---------------------------------------------------------------------------


@pytest.mark.real_file
def test_real_cv_golden() -> None:
    """Rendered XML must match the stored golden file.

    On the first run the golden file is created automatically; subsequent runs
    compare output against it.
    """
    data = _INPUT_DOCX.read_bytes()
    src = BytesSource(data)
    resp = _service().process(src, "CV_Test_1.docx")
    current_xml: str = resp.xml

    if not _GOLDEN_XML.exists():
        _GOLDEN_XML.parent.mkdir(parents=True, exist_ok=True)
        _GOLDEN_XML.write_text(current_xml, encoding="utf-8")
        pytest.skip(f"Golden file created at {_GOLDEN_XML} — re-run to compare")

    golden_xml = _GOLDEN_XML.read_text(encoding="utf-8")
    assert current_xml == golden_xml, f"Rendered XML does not match the golden file. Delete {_GOLDEN_XML} and re-run to regenerate."
