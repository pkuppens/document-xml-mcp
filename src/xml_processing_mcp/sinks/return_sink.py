"""In-memory return sink."""


class ReturnSink:
    """Sink that holds the XML in memory and returns it."""

    def __init__(self) -> None:
        self._last_xml: str | None = None

    def write_xml(self, document_id: str, xml: str) -> str:
        self._last_xml = xml
        return xml

    @property
    def last_xml(self) -> str | None:
        return self._last_xml
