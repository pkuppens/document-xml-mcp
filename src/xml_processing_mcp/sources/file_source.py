"""File-based document source with directory allow-list."""

from pathlib import Path


class FileSource:
    """Source that reads a document from a local file path.

    Only paths inside one of the allowed directories are permitted.
    """

    def __init__(self, path: str, allowed_dirs: list[str]) -> None:
        self._path = self._validate(path, allowed_dirs)

    @staticmethod
    def _validate(path: str, allowed_dirs: list[str]) -> Path:
        resolved = Path(path).resolve()
        for allowed in allowed_dirs:
            if resolved.is_relative_to(Path(allowed).resolve()):
                return resolved
        raise ValueError(f"Path '{path}' is not within any allowed directory: {allowed_dirs}")

    def get_document_bytes(self) -> bytes:
        return self._path.read_bytes()
