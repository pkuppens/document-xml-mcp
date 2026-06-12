"""Tests for the normalised document tree."""

from xml_processing_mcp.document_tree.builder import make_node
from xml_processing_mcp.document_tree.nodes import VALID_TAGS, DocumentNode


def test_make_node_tag_and_text():
    node = make_node("paragraph", "Hello world")
    assert node.tag == "paragraph"
    assert node.text == "Hello world"
    assert node.attributes == {}
    assert node.children == []


def test_make_node_with_attrs():
    node = make_node("heading", "Title", level="1")
    assert node.attributes == {"level": "1"}


def test_make_node_no_text():
    node = make_node("table")
    assert node.text is None


def test_children_can_be_appended():
    parent = make_node("body")
    child = make_node("paragraph", "text")
    parent.children.append(child)
    assert len(parent.children) == 1
    assert parent.children[0].tag == "paragraph"


def test_document_node_is_dataclass():
    node = DocumentNode(tag="document")
    assert node.tag == "document"
    assert node.attributes == {}
    assert node.children == []


def test_valid_tags_contains_expected():
    for tag in ("document", "body", "heading", "paragraph", "list", "item", "table", "row", "cell"):
        assert tag in VALID_TAGS
