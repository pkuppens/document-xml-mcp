"""Tests for the CV XML field extractor."""

import asyncio

import pytest

from xml_processing_mcp.server import extract_cv_fields, mcp
from xml_processing_mcp.services.cv_field_extractor import extract_cv_fields as _extract

# Full CV XML with all common sections
_FULL_CV_XML = """<document><body>
  <heading level="1" class="Title">Jane Doe</heading>
  <section class="Heading1" title="Contact">
    <paragraph>jane.doe@example.com | +31 6 12345678 | linkedin.com/in/janedoe | Amsterdam</paragraph>
  </section>
  <section class="Heading1" title="Profile">
    <paragraph>Senior Data Engineer with 5 years of Python and cloud experience.</paragraph>
  </section>
  <section class="Heading1" title="Skills">
    <list>
      <item>Python</item>
      <item>SQL</item>
      <item>Apache Spark</item>
      <item>AWS</item>
    </list>
  </section>
  <section class="Heading1" title="Experience">
    <table>
      <row><cell>2020 – present</cell><cell>Data Engineer</cell><cell>Acme Corp</cell><cell>Built pipelines</cell></row>
      <row><cell>2018 – 2020</cell><cell>Junior Developer</cell><cell>StartupXYZ</cell><cell>Python development</cell></row>
    </table>
  </section>
  <section class="Heading1" title="Education">
    <table>
      <row><cell>2018</cell><cell>MSc Computer Science</cell><cell>TU Delft</cell></row>
    </table>
  </section>
  <section class="Heading1" title="Languages">
    <list>
      <item>Dutch — Native</item>
      <item>English — Fluent</item>
    </list>
  </section>
  <section class="Heading1" title="Certifications">
    <list>
      <item>AWS Solutions Architect (2022)</item>
    </list>
  </section>
</body></document>"""

# CV XML missing the Skills section
_CV_XML_NO_SKILLS = """<document><body>
  <heading level="1" class="Title">John Smith</heading>
  <section class="Heading1" title="Experience">
    <paragraph>Software developer at Corp Inc 2021-2024</paragraph>
  </section>
</body></document>"""

# CV XML with no name heading
_CV_XML_NO_NAME = """<document><body>
  <section class="Heading1" title="Skills">
    <list><item>Java</item></list>
  </section>
</body></document>"""


# --- service-level unit tests ---


def test_extract_full_cv_name():
    result = _extract(_FULL_CV_XML)
    assert result["name"] == "Jane Doe"


def test_extract_full_cv_email():
    result = _extract(_FULL_CV_XML)
    assert result["contact"]["email"] == "jane.doe@example.com"


def test_extract_full_cv_phone():
    result = _extract(_FULL_CV_XML)
    assert result["contact"]["phone"] is not None
    assert "6" in result["contact"]["phone"]


def test_extract_full_cv_linkedin():
    result = _extract(_FULL_CV_XML)
    assert result["contact"]["linkedin"] == "linkedin.com/in/janedoe"


def test_extract_full_cv_summary():
    result = _extract(_FULL_CV_XML)
    assert result["summary"] is not None
    assert "Data Engineer" in result["summary"]


def test_extract_full_cv_skills():
    result = _extract(_FULL_CV_XML)
    assert "Python" in result["skills"]
    assert "SQL" in result["skills"]
    assert len(result["skills"]) >= 4


def test_extract_full_cv_experience_count():
    result = _extract(_FULL_CV_XML)
    assert len(result["experience"]) == 2


def test_extract_full_cv_experience_period():
    result = _extract(_FULL_CV_XML)
    periods = [e["period"] for e in result["experience"] if e["period"]]
    assert any("2020" in p for p in periods)


def test_extract_full_cv_education():
    result = _extract(_FULL_CV_XML)
    assert len(result["education"]) >= 1
    degrees = [e["degree"] for e in result["education"] if e["degree"]]
    assert any("MSc" in d or "Computer Science" in d for d in degrees)


def test_extract_full_cv_languages():
    result = _extract(_FULL_CV_XML)
    assert len(result["languages"]) >= 1
    assert any("Dutch" in lang for lang in result["languages"])


def test_extract_full_cv_certifications():
    result = _extract(_FULL_CV_XML)
    assert len(result["certifications"]) >= 1
    assert any("AWS" in c for c in result["certifications"])


def test_extract_full_cv_no_warnings():
    result = _extract(_FULL_CV_XML)
    assert result["warnings"] == []


def test_extract_missing_skills_produces_warning():
    result = _extract(_CV_XML_NO_SKILLS)
    assert any("skills" in w.lower() for w in result["warnings"])


def test_extract_missing_name_produces_warning():
    result = _extract(_CV_XML_NO_NAME)
    assert result["name"] is None
    assert any("name" in w.lower() for w in result["warnings"])


def test_extract_malformed_xml_raises_value_error():
    with pytest.raises(ValueError, match="Invalid XML"):
        _extract("<document><unclosed>")


def test_extract_empty_xml_raises_value_error():
    with pytest.raises(ValueError):
        _extract("")


# --- MCP tool tests ---


def test_mcp_tool_extract_cv_fields_full_cv():
    result = extract_cv_fields(xml=_FULL_CV_XML)
    assert result["name"] == "Jane Doe"
    assert result["skills"]
    assert result["experience"]


def test_mcp_tool_extract_cv_fields_malformed_raises():
    with pytest.raises(Exception):
        extract_cv_fields(xml="not xml at all")


def test_mcp_tool_is_registered():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert "extract_cv_fields" in names
