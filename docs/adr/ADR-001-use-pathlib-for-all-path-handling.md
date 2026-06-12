# ADR-001 — Use pathlib.Path for all path handling

| Field | Value |
|-------|-------|
| Status | Accepted |
| Date | 2026-06-12 |
| Deciders | Pieter Kuppens |

---

## Context

The server runs on Windows, Linux, and macOS (locally and in Docker).
Path handling via plain strings is error-prone across platforms:

- Windows uses `\` as separator; POSIX uses `/`.
- Windows paths have drive letters (`C:\`); UNC paths start with `\\`.
- `os.path` functions return strings, requiring repeated `str()` / `join()` calls.
- String-based extension checks (`str.endswith(".docx")`) miss case variations
  and break on full paths (`/input/cv.docx` does not end with `.docx` after naive split).
- Detecting whether a string is an absolute path requires separate logic for
  Windows drives, UNC paths, and POSIX roots — all easy to get wrong with regex.

These issues surfaced concretely during development:

1. `check_extension` originally used `str.endswith`, which failed when a full
   Windows path was passed as the filename argument.
2. `Base64Source` initially used a `re.VERBOSE` pattern to detect file paths in
   `content_base64`; the pattern silently failed for POSIX (`/`) and UNC (`\\`)
   paths due to whitespace-handling edge cases in verbose mode.
3. Documentation examples used `C:\Users\piete\Downloads\...` as the test path,
   exposing a username and breaking for colleagues on different machines.

---

## Decision

**Use `pathlib.Path` (and `pathlib.PureWindowsPath` where needed) for all path
operations throughout the codebase. Never manipulate path strings directly.**

### Rules

| Operation | Use | Not |
|-----------|-----|-----|
| Join path segments | `Path(a) / b` | `os.path.join(a, b)` or `a + "/" + b` |
| Get file extension | `Path(f).suffix` | `f.split(".")[-1]` or `f.endswith(".docx")` |
| Get filename without extension | `Path(f).stem` | string slicing |
| Get parent directory | `Path(f).parent` | `os.path.dirname(f)` |
| Resolve to absolute | `Path(f).resolve()` | `os.path.abspath(f)` |
| Check if file exists | `Path(f).exists()` | `os.path.exists(f)` |
| Check if inside a directory | `p.is_relative_to(base)` | string prefix checks |
| Detect absolute path (cross-platform) | `Path(s).is_absolute() or PureWindowsPath(s).is_absolute()` | manual regex or `startswith` |
| Read file bytes | `Path(f).read_bytes()` | `open(f, "rb").read()` |
| Write file text | `Path(f).write_text(s, encoding="utf-8")` | `open(f, "w").write(s)` |

### Cross-platform absolute-path detection

When running on Linux/macOS, `Path("C:\\Users\\cv.docx").is_absolute()` returns
`False` because the OS treats backslashes as filename characters.
Use both:

```python
from pathlib import Path, PureWindowsPath

def is_absolute_on_any_platform(s: str) -> bool:
    return Path(s).is_absolute() or PureWindowsPath(s).is_absolute()
```

`PureWindowsPath` is a pure (non-I/O) class available on all platforms.
It recognises Windows drives (`C:\`), UNC paths (`\\server\share`), and
POSIX-style roots (`/`) as absolute — covering every case without I/O.

### Relative paths for local development

Prefer project-relative paths (e.g. `input/cv.docx`) over user-specific absolute
paths (e.g. `C:\Users\piete\Downloads\cv.docx`).

- Relative paths work identically for every developer.
- They do not expose usernames or machine-specific directory layouts.
- `Path("input/cv.docx").resolve()` converts them to absolute at runtime,
  relative to the server's working directory (the project root when launched
  with `uv run document-xml-mcp`).

The project ships an `input/` directory (gitignored except `.gitkeep`) for this
purpose. Copy test files there; do not commit them.

---

## Consequences

### Positive

- Single, consistent API for all path operations.
- Automatic separator translation: `Path("input") / "cv.docx"` produces
  `input\cv.docx` on Windows and `input/cv.docx` on Linux/macOS.
- `Path.suffix`, `Path.stem`, `Path.name` replace error-prone string splits.
- `Path.is_relative_to()` replaces manual prefix checks for allow-list validation.
- Code is shorter and more readable.

### Negative / watch-outs

- `PureWindowsPath` must be imported explicitly when cross-platform absolute-path
  detection is needed (e.g. in `Base64Source`).
- `Path.resolve()` performs I/O (resolves symlinks, expands `..`). Use
  `PurePath` variants for purely syntactic operations where no I/O is wanted.
- Pydantic model fields that hold paths should remain `str` for JSON
  serialisation; convert to `Path` at the point of use, not at the model level.

---

## Compliance checklist

| Module | Status | Notes |
|--------|--------|-------|
| `security/file_limits.py` | ✅ | `Path(filename).suffix` for extension check |
| `sources/file_source.py` | ✅ | `Path.resolve()` + `is_relative_to()` |
| `sources/bytes_source.py` | ✅ | `Path.is_absolute()` + `PureWindowsPath.is_absolute()` |
| `sinks/file_sink.py` | ✅ | `Path.resolve()`, `Path.mkdir()`, `Path.write_text()` |
| `server.py` | ✅ | `Path.resolve()`, `Path.name`, `Path.stem`, glob |
| `parsers/docx_parser.py` | ✅ | No path operations (works on bytes) |
| `renderers/` | ✅ | No path operations |

---

## References

- [pathlib — Object-oriented filesystem paths](https://docs.python.org/3/library/pathlib.html)
- [PEP 428 — The pathlib module](https://peps.python.org/pep-0428/)
- `src/xml_processing_mcp/sources/bytes_source.py` — cross-platform path detection
- `src/xml_processing_mcp/security/file_limits.py` — extension check with `Path.suffix`
