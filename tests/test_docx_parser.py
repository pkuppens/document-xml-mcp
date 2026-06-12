"""Tests for the DOCX parser."""

import io
import zipfile

import pytest

from xml_processing_mcp.parsers.docx_parser import DocxParser

# Minimal WordprocessingML document used across tests
_DOCUMENT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:r><w:t>Main Title</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>First paragraph.</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Second paragraph.</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>
      <w:r><w:t>List item one</w:t></w:r>
    </w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>A1</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>B1</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>A2</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>B2</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
    <w:p>
      <w:hyperlink r:id="rId1">
        <w:r><w:t>Click here</w:t></w:r>
      </w:hyperlink>
    </w:p>
  </w:body>
</w:document>"""


def _make_docx(document_xml: bytes = _DOCUMENT_XML) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", document_xml)
        zf.writestr("[Content_Types].xml", b"<Types/>")
    return buf.getvalue()


@pytest.fixture
def parsed():
    return DocxParser().parse(_make_docx())


def _flatten(node, acc=None):
    if acc is None:
        acc = []
    acc.append(node)
    for child in node.children:
        _flatten(child, acc)
    return acc


def test_root_tag(parsed):
    assert parsed.tag == "document"


def test_body_child(parsed):
    assert parsed.children[0].tag == "body"


def test_heading_detected(parsed):
    nodes = _flatten(parsed)
    headings = [n for n in nodes if n.tag == "heading"]
    assert len(headings) == 1
    assert headings[0].text == "Main Title"
    assert headings[0].attributes.get("level") == "1"


def test_paragraphs_in_order(parsed):
    body = parsed.children[0]
    para_texts = [n.text for n in body.children if n.tag == "paragraph"]
    assert para_texts == ["First paragraph.", "Second paragraph."]


def test_list_item_detected(parsed):
    nodes = _flatten(parsed)
    items = [n for n in nodes if n.tag == "item"]
    assert len(items) >= 1
    assert items[0].text == "List item one"


def test_table_structure(parsed):
    nodes = _flatten(parsed)
    tables = [n for n in nodes if n.tag == "table"]
    assert len(tables) == 1
    table = tables[0]
    assert len(table.children) == 2  # two rows
    for row in table.children:
        assert row.tag == "row"
        assert len(row.children) == 2  # two cells


def test_link_detected(parsed):
    nodes = _flatten(parsed)
    links = [n for n in nodes if n.tag == "link"]
    assert len(links) == 1
    assert links[0].text == "Click here"
