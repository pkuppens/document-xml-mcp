"""File size and extension validation."""

_DOCM_SUFFIX = ".docm"


def check_file_size(data: bytes, max_mb: int) -> None:
    """Raise ValueError if data exceeds max_mb megabytes."""
    limit = max_mb * 1024 * 1024
    if len(data) > limit:
        raise ValueError(f"File size {len(data)} bytes exceeds limit of {max_mb} MB ({limit} bytes)")


def check_extension(filename: str, allowed: list[str] | None = None) -> None:
    """Raise ValueError if filename has a disallowed or dangerous extension."""
    if allowed is None:
        allowed = [".docx"]
    lower = filename.lower()
    if lower.endswith(_DOCM_SUFFIX):
        raise ValueError(f"Macro-enabled documents (.docm) are not allowed: {filename}")
    for ext in allowed:
        if lower.endswith(ext.lower()):
            return
    raise ValueError(f"Unsupported file extension for '{filename}'. Allowed: {allowed}")
