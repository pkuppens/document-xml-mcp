"""In-memory document sources."""

import base64
import logging
from pathlib import Path, PureWindowsPath

_log = logging.getLogger(__name__)


def _looks_like_path(value: str) -> bool:
    """Return True if value looks like an absolute file path rather than base64 content."""
    s = value.strip().strip("\"'")
    if not s:
        return False
    # Path("/posix/path").is_absolute() returns False on Windows; check explicitly.
    if s[0] == "/":
        return True
    return Path(s).is_absolute() or PureWindowsPath(s).is_absolute()


class BytesSource:
    """Source backed by raw bytes."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def get_document_bytes(self) -> bytes:
        _log.debug("BytesSource.get_document_bytes size=%d", len(self._data))
        return self._data


class Base64Source:
    """Source backed by a base64-encoded string.

    content_base64 must contain the BASE64-ENCODED FILE CONTENT, not a file path.
    To parse a file by path use parse_file_to_xml instead.
    """

    def __init__(self, encoded: str) -> None:
        self._encoded = encoded

    def get_document_bytes(self) -> bytes:
        _log.debug("Base64Source.get_document_bytes encoded_len=%d", len(self._encoded))

        if _looks_like_path(self._encoded):
            _log.warning(
                "Base64Source: content_base64 looks like a file path %r — use parse_file_to_xml to parse files by path",
                self._encoded[:120],
            )
            raise ValueError(
                f"content_base64 looks like a file path ({self._encoded.strip()!r}). "
                "To parse a local file use the parse_file_to_xml tool instead, "
                "or encode the file contents as base64 first."
            )

        data = base64.b64decode(self._encoded)
        _log.debug("Base64Source.get_document_bytes decoded_len=%d first_4_bytes=%r", len(data), data[:4])
        return data
