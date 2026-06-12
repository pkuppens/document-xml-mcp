"""XmlSink protocol."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class XmlSink(Protocol):
    """Receives generated XML output."""

    def write_xml(self, document_id: str, xml: str) -> str | None: ...
