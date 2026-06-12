"""DocumentParser protocol."""

from typing import Protocol

from xml_processing_mcp.document_tree.nodes import DocumentNode


class DocumentParser(Protocol):
    """Parses document bytes into a normalised DocumentNode tree."""

    def parse(self, document_bytes: bytes) -> DocumentNode: ...
