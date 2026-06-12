"""In-memory document sources."""

import base64


class BytesSource:
    """Source backed by raw bytes."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def get_document_bytes(self) -> bytes:
        return self._data


class Base64Source:
    """Source backed by a base64-encoded string."""

    def __init__(self, encoded: str) -> None:
        self._encoded = encoded

    def get_document_bytes(self) -> bytes:
        return base64.b64decode(self._encoded)
