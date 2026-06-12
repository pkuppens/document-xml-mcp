"""File size and extension validation."""

import logging
from pathlib import Path

_log = logging.getLogger(__name__)

_DOCM_SUFFIX = ".docm"


def check_file_size(data: bytes, max_mb: int) -> None:
    """Raise ValueError if data exceeds max_mb megabytes."""
    limit = max_mb * 1024 * 1024
    if len(data) > limit:
        raise ValueError(f"File size {len(data)} bytes exceeds limit of {max_mb} MB ({limit} bytes)")


def _parse_filename(filename: str) -> Path:
    """Strip surrounding whitespace and quotes, then return a Path.

    Raises ValueError (with debug log) if the result is empty.
    """
    cleaned = filename.strip().strip("\"'")
    _log.debug("check_extension: raw=%r cleaned=%r", filename, cleaned)
    if not cleaned:
        raise ValueError(f"Filename is empty after stripping whitespace/quotes: {filename!r}")
    try:
        return Path(cleaned)
    except Exception as exc:
        _log.debug("check_extension: Path() failed for %r: %s", cleaned, exc)
        raise ValueError(f"Cannot parse filename {cleaned!r} as a path: {exc}") from exc


def check_extension(filename: str, allowed: list[str] | None = None) -> None:
    """Raise ValueError if filename has a disallowed or dangerous extension.

    Uses Path.suffix for reliable cross-platform extension extraction.
    Strips surrounding whitespace and quotes before parsing.
    """
    if allowed is None:
        allowed = [".docx"]

    path = _parse_filename(filename)
    suffix = path.suffix.lower()
    _log.debug("check_extension: suffix=%r allowed=%r", suffix, allowed)

    if suffix == _DOCM_SUFFIX:
        raise ValueError(f"Macro-enabled documents (.docm) are not allowed: {filename!r}")
    if suffix in {ext.lower() for ext in allowed}:
        return
    raise ValueError(f"Unsupported file extension {suffix!r} for {filename!r}. Allowed: {allowed}")
