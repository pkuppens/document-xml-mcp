"""File-based document source with directory allow-list."""

import logging
from pathlib import Path

_log = logging.getLogger(__name__)


class FileSource:
    """Source that reads a document from a local file path.

    Only paths inside one of the allowed directories are permitted.
    NOTE: The path must be accessible on the SERVER's filesystem.
    """

    def __init__(self, path: str, allowed_dirs: list[str]) -> None:
        self._path = self._validate(path, allowed_dirs)

    @staticmethod
    def _validate(path: str, allowed_dirs: list[str]) -> Path:
        resolved = Path(path).resolve()
        _log.debug("FileSource._validate path=%r resolved=%s allowed_dirs=%s", path, resolved, allowed_dirs)
        for allowed in allowed_dirs:
            if resolved.is_relative_to(Path(allowed).resolve()):
                _log.debug("FileSource._validate path allowed under %r", allowed)
                return resolved
        _log.debug("FileSource._validate path rejected: not under any allowed dir")
        raise ValueError(f"Path '{path}' is not within any allowed directory: {allowed_dirs}")

    def get_document_bytes(self) -> bytes:
        _log.debug("FileSource.get_document_bytes path=%s exists=%s", self._path, self._path.exists())
        data = self._path.read_bytes()
        _log.debug("FileSource.get_document_bytes read size=%d", len(data))
        return data
