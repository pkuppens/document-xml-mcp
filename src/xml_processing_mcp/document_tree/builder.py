"""Convenience builder for DocumentNode instances."""

from xml_processing_mcp.document_tree.nodes import DocumentNode


def make_node(tag: str, text: str | None = None, **attrs: str) -> DocumentNode:
    """Create a DocumentNode with optional text and keyword attributes."""
    return DocumentNode(tag=tag, text=text, attributes=dict(attrs))
