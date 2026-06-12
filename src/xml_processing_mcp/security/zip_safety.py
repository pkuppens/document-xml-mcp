"""Safe DOCX ZIP opening with path-traversal and ZIP-bomb guards."""

import io
import zipfile

_MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024  # 200 MB hard limit against ZIP bombs


def safe_open_docx(data: bytes) -> zipfile.ZipFile:
    """Open DOCX bytes as a ZipFile after safety checks.

    Raises ValueError for invalid ZIPs, path traversal entries, or ZIP bombs.
    """
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise ValueError("Input is not a valid ZIP/DOCX file")

    zf = zipfile.ZipFile(io.BytesIO(data))

    total_uncompressed = 0
    for info in zf.infolist():
        if ".." in info.filename or info.filename.startswith("/"):
            zf.close()
            raise ValueError(f"Suspicious ZIP entry (path traversal): '{info.filename}'")
        total_uncompressed += info.file_size
        if total_uncompressed > _MAX_UNCOMPRESSED_BYTES:
            zf.close()
            raise ValueError(
                f"ZIP uncompressed size exceeds {_MAX_UNCOMPRESSED_BYTES // (1024 * 1024)} MB — possible ZIP bomb"
            )

    return zf
