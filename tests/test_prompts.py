"""Tests for CV prompt templates registered in server.py."""

import asyncio

from xml_processing_mcp.prompts.cv_analysis import analyze_cv_gaps_prompt, answer_cv_questions_prompt
from xml_processing_mcp.prompts.cv_generation import rewrite_cv_for_assignment_prompt, write_motivation_letter_prompt
from xml_processing_mcp.server import mcp

_CV_XML = """<document><body>
  <heading level="1" class="Title">Jane Doe</heading>
  <section class="Heading1" title="Skills">
    <list><item>Python</item><item>SQL</item></list>
  </section>
  <section class="Heading1" title="Experience">
    <paragraph>Data Engineer at Acme Corp 2020-2023</paragraph>
  </section>
</body></document>"""

_JOB = "Senior ML Engineer. Requirements: Python, TensorFlow, Kubernetes, 5+ years experience."
_QUESTION = "How many years of Python experience does the candidate have?"
_ASSIGNMENT = "Senior Data Engineer at HealthCorp. Requirements: Python, Spark, healthcare domain knowledge."


# --- unit tests: prompt functions return valid message lists ---


def test_analyze_cv_gaps_returns_user_message():
    messages = analyze_cv_gaps_prompt(_CV_XML, _JOB)
    assert len(messages) >= 1
    assert messages[0]["role"] == "user"
    assert _CV_XML in messages[0]["content"]
    assert _JOB in messages[0]["content"]


def test_analyze_cv_gaps_mentions_gap_analysis():
    messages = analyze_cv_gaps_prompt(_CV_XML, _JOB)
    content = messages[0]["content"].lower()
    assert "gap" in content or "missing" in content or "absent" in content


def test_answer_cv_questions_includes_question_and_cv():
    messages = answer_cv_questions_prompt(_CV_XML, _QUESTION)
    assert len(messages) >= 1
    assert messages[0]["role"] == "user"
    assert _QUESTION in messages[0]["content"]
    assert _CV_XML in messages[0]["content"]


def test_write_motivation_letter_default_tone():
    messages = write_motivation_letter_prompt(_CV_XML, _ASSIGNMENT)
    assert len(messages) >= 1
    assert messages[0]["role"] == "user"
    content = messages[0]["content"]
    assert _CV_XML in content
    assert _ASSIGNMENT in content
    assert "motivation" in content.lower() or "letter" in content.lower()


def test_write_motivation_letter_concise_tone():
    messages = write_motivation_letter_prompt(_CV_XML, _ASSIGNMENT, tone="concise")
    content = messages[0]["content"]
    assert "250" in content or "concise" in content.lower() or "tight" in content.lower()


def test_write_motivation_letter_unknown_tone_falls_back():
    # Unknown tone should not raise; defaults to professional
    messages = write_motivation_letter_prompt(_CV_XML, _ASSIGNMENT, tone="weird_tone")
    assert len(messages) >= 1


def test_rewrite_cv_xml_format():
    messages = rewrite_cv_for_assignment_prompt(_CV_XML, _ASSIGNMENT, target_format="xml")
    content = messages[0]["content"]
    assert "xml" in content.lower()
    assert _CV_XML in content
    assert _ASSIGNMENT in content


def test_rewrite_cv_markdown_format():
    messages = rewrite_cv_for_assignment_prompt(_CV_XML, _ASSIGNMENT, target_format="markdown")
    content = messages[0]["content"]
    assert "markdown" in content.lower()


# --- MCP layer: verify prompts are discoverable via mcp.list_prompts() ---


def test_mcp_lists_four_cv_prompts():
    prompts = asyncio.run(mcp.list_prompts())
    names = {p.name for p in prompts}
    assert "analyze_cv_gaps" in names
    assert "answer_cv_questions" in names
    assert "write_motivation_letter" in names
    assert "rewrite_cv_for_assignment" in names


def test_mcp_get_analyze_cv_gaps_returns_messages():
    result = asyncio.run(mcp.get_prompt("analyze_cv_gaps", {"cv_xml": _CV_XML, "job_description": _JOB}))
    assert result.messages
    assert result.messages[0].role == "user"


def test_mcp_get_write_motivation_letter_returns_messages():
    result = asyncio.run(mcp.get_prompt("write_motivation_letter", {"cv_xml": _CV_XML, "assignment": _ASSIGNMENT}))
    assert result.messages
    assert result.messages[0].role == "user"


def test_mcp_get_answer_cv_questions_returns_messages():
    result = asyncio.run(mcp.get_prompt("answer_cv_questions", {"cv_xml": _CV_XML, "question": _QUESTION}))
    assert result.messages
    assert result.messages[0].role == "user"


def test_mcp_get_rewrite_cv_for_assignment_returns_messages():
    result = asyncio.run(mcp.get_prompt("rewrite_cv_for_assignment", {"cv_xml": _CV_XML, "assignment": _ASSIGNMENT}))
    assert result.messages
    assert result.messages[0].role == "user"
