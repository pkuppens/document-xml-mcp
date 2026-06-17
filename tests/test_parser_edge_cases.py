"""Edge-case tests for DocxParser.

Covers:
- Empty / whitespace-only documents  (Task 13.1)
- Heading style variants             (Task 13.2)
- List grouping and continuity       (Task 13.3)
"""

import io
import zipfile

from xml_processing_mcp.parsers.docx_parser import DocxParser
from xml_processing_mcp.renderers.simple_xml_renderer import SimpleXmlRenderer

_W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _make_docx(document_xml: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", document_xml)
        zf.writestr("[Content_Types].xml", b"<Types/>")
    return buf.getvalue()


def _flatten(node, acc=None):
    if acc is None:
        acc = []
    acc.append(node)
    for child in node.children:
        _flatten(child, acc)
    return acc


def _parse(xml: bytes) -> object:
    return DocxParser().parse(_make_docx(xml))


# ---------------------------------------------------------------------------
# Task 13.1 — Empty and whitespace-only documents
# ---------------------------------------------------------------------------


def test_empty_body():
    """<w:body/> with no children → body node has no children."""
    xml = f"<w:document {_W_NS}><w:body/></w:document>".encode()
    doc = _parse(xml)
    body = doc.children[0]
    assert body.tag == "body"
    assert body.children == []


def test_whitespace_only_paragraphs():
    """Paragraph whose only text run is whitespace is added to the tree (text is truthy),
    but the renderer drops it because node.text.strip() is falsy.

    Behaviour: DocxParser adds the paragraph node; SimpleXmlRenderer removes it.
    """
    xml = (f"<w:document {_W_NS}><w:body><w:p><w:r><w:t>   </w:t></w:r></w:p></w:body></w:document>").encode()
    doc = _parse(xml)
    # Parser adds it (whitespace is truthy in Python)
    nodes = _flatten(doc)
    paragraphs = [n for n in nodes if n.tag == "paragraph"]
    assert len(paragraphs) == 1
    assert paragraphs[0].text == "   "

    # Renderer drops it because text.strip() == ""
    rendered = SimpleXmlRenderer().render(doc)
    assert "<paragraph" not in rendered


def test_paragraph_with_empty_runs():
    """<w:r/> run with no <w:t> → _collect_text returns '' → paragraph NOT added to body.

    The parser's ``if text:`` guard drops paragraphs with no collected text.
    """
    xml = (f"<w:document {_W_NS}><w:body><w:p><w:r/></w:p></w:body></w:document>").encode()
    doc = _parse(xml)
    nodes = _flatten(doc)
    paragraphs = [n for n in nodes if n.tag == "paragraph"]
    assert paragraphs == []


def test_table_with_empty_cells():
    """2×2 table with no text in any cell → table and row nodes present; cell nodes present
    (cells are always added, even when cell_text is empty — text is set to None)."""
    xml = (
        f"<w:document {_W_NS}>"
        "<w:body>"
        "<w:tbl>"
        "<w:tr><w:tc><w:p/></w:tc><w:tc><w:p/></w:tc></w:tr>"
        "<w:tr><w:tc><w:p/></w:tc><w:tc><w:p/></w:tc></w:tr>"
        "</w:tbl>"
        "</w:body>"
        "</w:document>"
    ).encode()
    doc = _parse(xml)
    nodes = _flatten(doc)

    tables = [n for n in nodes if n.tag == "table"]
    assert len(tables) == 1
    table = tables[0]
    assert len(table.children) == 2  # two rows

    for row in table.children:
        assert row.tag == "row"
        assert len(row.children) == 2  # two cells
        for cell in row.children:
            assert cell.tag == "cell"
            assert cell.text is None  # no text was collected


def test_no_body_element():
    """Document XML without <w:body> → document with one empty body child."""
    xml = f"<w:document {_W_NS}/>".encode()
    doc = _parse(xml)
    assert doc.tag == "document"
    assert doc.children[0].tag == "body"
    assert doc.children[0].children == []


# ---------------------------------------------------------------------------
# Task 13.2 — Heading style variants
# ---------------------------------------------------------------------------


def _heading_xml(style_val: str, text: str = "Heading Text") -> bytes:
    return (
        f"<w:document {_W_NS}>"
        "<w:body>"
        "<w:p>"
        f'<w:pPr><w:pStyle w:val="{style_val}"/></w:pPr>'
        f"<w:r><w:t>{text}</w:t></w:r>"
        "</w:p>"
        "</w:body>"
        "</w:document>"
    ).encode()


def test_heading_style_no_space():
    """pStyle 'Heading1' → tag=heading, level attribute='1'."""
    doc = _parse(_heading_xml("Heading1"))
    nodes = _flatten(doc)
    headings = [n for n in nodes if n.tag == "heading"]
    assert len(headings) == 1
    assert headings[0].attributes["level"] == "1"


def test_heading_style_with_space():
    """pStyle 'Heading 1' → tag=heading, level attribute='1'.

    The digit extraction strips non-digit chars, so 'Heading 1' → level='1'.
    """
    doc = _parse(_heading_xml("Heading 1"))
    nodes = _flatten(doc)
    headings = [n for n in nodes if n.tag == "heading"]
    assert len(headings) == 1
    assert headings[0].attributes["level"] == "1"


def test_heading_style_lowercase():
    """pStyle 'heading2' → tag=heading, level attribute='2'.

    The parser checks ``style.startswith("heading")`` (lowercase), so this matches.
    """
    doc = _parse(_heading_xml("heading2"))
    nodes = _flatten(doc)
    headings = [n for n in nodes if n.tag == "heading"]
    assert len(headings) == 1
    assert headings[0].attributes["level"] == "2"


def test_non_heading_style():
    """pStyle 'Title' does not start with 'Heading' or 'heading' → tag=paragraph (not heading)."""
    doc = _parse(_heading_xml("Title", text="Document Title"))
    nodes = _flatten(doc)
    headings = [n for n in nodes if n.tag == "heading"]
    paragraphs = [n for n in nodes if n.tag == "paragraph"]
    assert headings == []
    assert len(paragraphs) == 1
    assert paragraphs[0].text == "Document Title"


def test_heading_level_extraction():
    """pStyle 'Heading10' → level attribute='10' (multi-digit levels work)."""
    doc = _parse(_heading_xml("Heading10"))
    nodes = _flatten(doc)
    headings = [n for n in nodes if n.tag == "heading"]
    assert len(headings) == 1
    assert headings[0].attributes["level"] == "10"


# ---------------------------------------------------------------------------
# Task 13.3 — List grouping and continuity
# ---------------------------------------------------------------------------


def _list_para(text: str) -> str:
    """Return a <w:p> with numPr (list item) and the given text."""
    return f'<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>'


def _plain_para(text: str) -> str:
    return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"


def test_list_items_grouped():
    """3 consecutive list items → exactly one <list> node with 3 <item> children."""
    xml = (
        f"<w:document {_W_NS}>"
        "<w:body>" + _list_para("Item A") + _list_para("Item B") + _list_para("Item C") + "</w:body>"
        "</w:document>"
    ).encode()
    doc = _parse(xml)
    nodes = _flatten(doc)
    lists = [n for n in nodes if n.tag == "list"]
    assert len(lists) == 1
    assert len(lists[0].children) == 3
    texts = [c.text for c in lists[0].children]
    assert texts == ["Item A", "Item B", "Item C"]


def test_list_interrupted_by_paragraph():
    """list item, plain paragraph, list item → two separate <list> nodes in body."""
    xml = (
        f"<w:document {_W_NS}>"
        "<w:body>" + _list_para("First") + _plain_para("Break paragraph") + _list_para("Second") + "</w:body>"
        "</w:document>"
    ).encode()
    doc = _parse(xml)
    nodes = _flatten(doc)
    lists = [n for n in nodes if n.tag == "list"]
    assert len(lists) == 2
    assert lists[0].children[0].text == "First"
    assert lists[1].children[0].text == "Second"


def test_list_item_empty_text():
    """List item with empty <w:t></w:t> → item node exists with text=None.

    _collect_text returns '' → ``text or None`` sets text=None on the item node.
    """
    xml = (
        f"<w:document {_W_NS}>"
        "<w:body>"
        "<w:p>"
        "<w:pPr><w:numPr>"
        '<w:ilvl w:val="0"/><w:numId w:val="1"/>'
        "</w:numPr></w:pPr>"
        "<w:r><w:t></w:t></w:r>"
        "</w:p>"
        "</w:body>"
        "</w:document>"
    ).encode()
    doc = _parse(xml)
    nodes = _flatten(doc)
    items = [n for n in nodes if n.tag == "item"]
    assert len(items) == 1
    assert items[0].text is None


def test_list_followed_by_table():
    """List item followed by a table → both present in correct order in body.children."""
    xml = (
        f"<w:document {_W_NS}>"
        "<w:body>" + _list_para("Only item") + "<w:tbl>"
        "<w:tr><w:tc><w:p><w:r><w:t>Cell</w:t></w:r></w:p></w:tc></w:tr>"
        "</w:tbl>" + "</w:body>"
        "</w:document>"
    ).encode()
    doc = _parse(xml)
    body = doc.children[0]
    assert body.children[0].tag == "list"
    assert body.children[1].tag == "table"
