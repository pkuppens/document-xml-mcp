"""DocumentSource protocol."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class DocumentSource(Protocol):
    """Provides raw document bytes."""

    def get_document_bytes(self) -> bytes: ...
