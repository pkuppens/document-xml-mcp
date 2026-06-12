"""Safe DOCX ZIP opening with path-traversal and ZIP-bomb guards."""

import io
import logging
import zipfile

_log = logging.getLogger(__name__)

_MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024  # 200 MB hard limit against ZIP bombs


def safe_open_docx(data: bytes) -> zipfile.ZipFile:
    """Open DOCX bytes as a ZipFile after safety checks.

    Raises ValueError for invalid ZIPs, path traversal entries, or ZIP bombs.
    """
    _log.debug("safe_open_docx checking %d bytes", len(data))

    if not zipfile.is_zipfile(io.BytesIO(data)):
        _log.debug("safe_open_docx rejected: not a ZIP (first 4 bytes: %r)", data[:4])
        raise ValueError(
            f"Input is not a valid ZIP/DOCX file "
            f"(received {len(data)} bytes; first 4 bytes: {data[:4]!r}). "
            "If submitting via base64, ensure there are no embedded newlines — "
            "on macOS pipe through: base64 -i file.docx | tr -d '\\n'"
        )

    zf = zipfile.ZipFile(io.BytesIO(data))
    entries = zf.infolist()
    _log.debug("safe_open_docx opened ZIP with %d entries", len(entries))

    total_uncompressed = 0
    for info in entries:
        _log.debug("safe_open_docx entry name=%r compressed=%d uncompressed=%d",
                   info.filename, info.compress_size, info.file_size)
        if ".." in info.filename or info.filename.startswith("/"):
            zf.close()
            _log.warning("safe_open_docx rejected: path traversal in entry %r", info.filename)
            raise ValueError(f"Suspicious ZIP entry (path traversal): '{info.filename}'")
        total_uncompressed += info.file_size
        if total_uncompressed > _MAX_UNCOMPRESSED_BYTES:
            zf.close()
            _log.warning("safe_open_docx rejected: ZIP bomb total_uncompressed=%d", total_uncompressed)
            raise ValueError(
                f"ZIP uncompressed size exceeds {_MAX_UNCOMPRESSED_BYTES // (1024 * 1024)} MB — possible ZIP bomb"
            )

    _log.debug("safe_open_docx passed all checks total_uncompressed=%d", total_uncompressed)
    return zf
