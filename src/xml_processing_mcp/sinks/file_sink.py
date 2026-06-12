"""File-based XML sink with directory allow-list."""

from pathlib import Path


class FileSink:
    """Sink that writes XML to a file in a configured output directory."""

    def __init__(self, output_dir: str, allowed_dirs: list[str]) -> None:
        self._output_dir = self._validate(output_dir, allowed_dirs)

    @staticmethod
    def _validate(output_dir: str, allowed_dirs: list[str]) -> Path:
        resolved = Path(output_dir).resolve()
        for allowed in allowed_dirs:
            if resolved == Path(allowed).resolve() or resolved.is_relative_to(Path(allowed).resolve()):
                return resolved
        raise ValueError(f"Output dir '{output_dir}' is not within any allowed directory: {allowed_dirs}")

    def write_xml(self, document_id: str, xml: str) -> str:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        out_path = self._output_dir / f"{Path(document_id).stem}.xml"
        out_path.write_text(xml, encoding="utf-8")
        return str(out_path)
