"""DocumentRenderer protocol."""

from typing import Protocol

from xml_processing_mcp.document_tree.nodes import DocumentNode


class DocumentRenderer(Protocol):
    """Renders a normalised document tree to a string."""

    def render(self, document: DocumentNode) -> str: ...
