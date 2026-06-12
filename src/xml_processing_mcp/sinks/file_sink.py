"""File-based XML sink with directory allow-list."""

import logging
from pathlib import Path

_log = logging.getLogger(__name__)


class FileSink:
    """Sink that writes XML to a file in a configured output directory."""

    def __init__(self, output_dir: str, allowed_dirs: list[str]) -> None:
        self._output_dir = self._validate(output_dir, allowed_dirs)

    @staticmethod
    def _validate(output_dir: str, allowed_dirs: list[str]) -> Path:
        resolved = Path(output_dir).resolve()
        _log.debug("FileSink._validate output_dir=%r resolved=%s allowed_dirs=%s", output_dir, resolved, allowed_dirs)
        for allowed in allowed_dirs:
            if resolved == Path(allowed).resolve() or resolved.is_relative_to(Path(allowed).resolve()):
                _log.debug("FileSink._validate output_dir allowed under %r", allowed)
                return resolved
        _log.debug("FileSink._validate output_dir rejected")
        raise ValueError(f"Output dir '{output_dir}' is not within any allowed directory: {allowed_dirs}")

    def write_xml(self, document_id: str, xml: str) -> str:
        out_path = self._output_dir / f"{Path(document_id).stem}.xml"
        _log.debug("FileSink.write_xml document_id=%r out_path=%s xml_len=%d", document_id, out_path, len(xml))
        self._output_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(xml, encoding="utf-8")
        _log.debug("FileSink.write_xml written ok")
        return str(out_path)
