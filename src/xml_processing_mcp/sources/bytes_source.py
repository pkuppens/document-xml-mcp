"""In-memory document sources."""

import base64
import logging

_log = logging.getLogger(__name__)


class BytesSource:
    """Source backed by raw bytes."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def get_document_bytes(self) -> bytes:
        _log.debug("BytesSource.get_document_bytes size=%d", len(self._data))
        return self._data


class Base64Source:
    """Source backed by a base64-encoded string."""

    def __init__(self, encoded: str) -> None:
        self._encoded = encoded

    def get_document_bytes(self) -> bytes:
        _log.debug("Base64Source.get_document_bytes encoded_len=%d", len(self._encoded))
        data = base64.b64decode(self._encoded)
        _log.debug("Base64Source.get_document_bytes decoded_len=%d first_4_bytes=%r", len(data), data[:4])
        return data
