"""Tests for SimpleXmlRenderer tree processor and serialiser."""

from lxml import etree

from xml_processing_mcp.document_tree.builder import make_node
from xml_processing_mcp.document_tree.nodes import DocumentNode
from xml_processing_mcp.renderers.simple_xml_renderer import SimpleXmlRenderer


def render(node):
    return SimpleXmlRenderer().render(node)


# --- Rule 1: remove empty nodes ---


def test_empty_leaf_removed():
    doc = make_node("document")
    doc.children.append(make_node("paragraph"))  # no text, no children
    result = render(doc)
    assert "<paragraph" not in result


def test_node_with_text_kept():
    doc = make_node("document")
    doc.children.append(make_node("paragraph", "Hello"))
    result = render(doc)
    assert "Hello" in result


# --- Rule 2: strip useless attributes ---


def test_empty_attr_stripped():
    node = make_node("paragraph", "text", style="")
    doc = DocumentNode(tag="document", children=[node])
    result = render(doc)
    assert 'style=""' not in result


def test_false_attr_stripped():
    node = make_node("paragraph", "text", visible="false")
    doc = DocumentNode(tag="document", children=[node])
    result = render(doc)
    assert "visible" not in result


def test_heading_level_kept_even_if_zero():
    node = make_node("heading", "Title", level="0", style="")
    doc = DocumentNode(tag="document", children=[node])
    result = render(doc)
    assert 'level="0"' in result
    assert "style" not in result


# --- Rule 3: promote single-child wrapper ---


def test_single_child_wrapper_promoted():
    # body -> section (no text, no attrs) -> paragraph "text"
    # section should be unwrapped; paragraph appears directly under body
    para = make_node("paragraph", "text")
    section = make_node("section")
    section.children.append(para)
    body = make_node("body")
    body.children.append(section)
    doc = make_node("document")
    doc.children.append(body)
    result = render(doc)
    # section should be gone; paragraph directly under body
    assert "<section" not in result
    assert "<paragraph>text</paragraph>" in result


def test_wrapper_not_promoted_if_has_attrs():
    para = make_node("paragraph", "text")
    section = make_node("section", **{"class": "intro"})
    section.children.append(para)
    doc = DocumentNode(tag="document", children=[section])
    result = render(doc)
    assert "<section" in result


# --- XML validity ---


def test_output_is_valid_xml():
    doc = make_node("document")
    body = make_node("body")
    body.children.append(make_node("heading", "Title", level="1"))
    body.children.append(make_node("paragraph", "Some text."))
    doc.children.append(body)
    xml = render(doc)
    parsed = etree.fromstring(xml.encode())
    assert parsed.tag == "document"


# --- Realistic round-trip ---


def test_realistic_tree():
    doc = make_node("document")
    body = make_node("body")
    body.children.append(make_node("heading", "Jane Doe", level="1"))
    body.children.append(make_node("paragraph", "Software engineer."))
    table = make_node("table")
    row = make_node("row")
    row.children.append(make_node("cell", "Year"))
    row.children.append(make_node("cell", "Role"))
    table.children.append(row)
    body.children.append(table)
    doc.children.append(body)

    xml = render(doc)
    root = etree.fromstring(xml.encode())
    assert root.find(".//heading") is not None
    assert root.find(".//table") is not None
    cells = root.findall(".//cell")
    assert len(cells) == 2
