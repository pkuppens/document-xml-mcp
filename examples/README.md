# examples/

Sample clients showing how to connect to the document-xml-mcp server.

## Scripts

| Script | Transport | Description |
|--------|-----------|-------------|
| [`client_stdio.py`](client_stdio.py) | stdio | Spawns the server as a child process; ideal for local use and CI |
| [`client_sse.py`](client_sse.py) | HTTP/SSE | Connects to an already-running server over HTTP; works with Docker, docker-compose, or a remote host |

---

## client_stdio.py

The client spawns `document-xml-mcp` as a child process via `uv run document-xml-mcp` and
communicates over stdin/stdout. No port or network setup required.

### Prerequisites

- `uv` on PATH
- Dependencies installed (`uv sync`)

### Usage

```bash
# List supported document types only
uv run python examples/client_stdio.py

# Full demo: parse a local DOCX file (exercises all four tools)
uv run python examples/client_stdio.py --docx input/CV_Test_1.docx
```

The `--docx` path is resolved on the local machine. The script automatically adds the file's
parent directory to `XML_PROCESSING_ALLOWED_INPUT_DIRS` so the server can access it.

---

## client_sse.py

The client connects to an already-running document-xml-mcp server over HTTP/SSE.

### Prerequisites

- The server must be running in SSE mode before the script starts.
- Port 8000 must be reachable from the machine running this script.

### Starting the server (pick one)

```bash
# Option A: local SSE mode
MCP_TRANSPORT=sse uv run document-xml-mcp

# Option B: Docker single container
MCP_TRANSPORT=sse docker compose up --build

# Option C: docker-compose with n8n profile (server auto-starts in SSE mode)
MCP_TRANSPORT=sse docker compose --profile n8n up --build
```

### Usage

```bash
# Connect to the default local SSE endpoint (http://localhost:8000/sse)
uv run python examples/client_sse.py

# Parse a DOCX file (file is read locally, sent as base64 — server needs no filesystem access)
uv run python examples/client_sse.py --docx input/CV_Test_1.docx

# Connect to a Docker container or remote host
uv run python examples/client_sse.py --url http://192.168.1.100:8000/sse --docx input/CV_Test_1.docx
```

### Docker path note

`parse_document_to_xml` (the base64 upload tool) works from any client regardless of where
the server runs — the file is encoded on the client side.

`parse_file_to_xml` and `parse_batch_to_xml` use **server-side paths**. When the server
runs in Docker, the host directory `./input/` is mounted read-only as `/input` inside the
container (see `docker-compose.yml`). Pass `/input/yourfile.docx` as the path argument for
these tools.

When running locally without Docker, paths are relative to the server's working directory
(the project root by default).

---

## Tool coverage

Both scripts exercise all four MCP tools:

| Tool | client_stdio.py | client_sse.py |
|------|:--------------:|:-------------:|
| `list_supported_document_types` | yes | yes |
| `parse_document_to_xml` (base64) | yes (requires `--docx`) | yes (requires `--docx`) |
| `parse_file_to_xml` | yes (requires `--docx`) | note printed only |
| `parse_batch_to_xml` | yes (requires `--docx`) | note printed only |

The SSE client focuses on the base64 upload tool because `parse_file_to_xml` and
`parse_batch_to_xml` require the file to exist on the server's filesystem, which makes
automated demos less portable in Docker/remote scenarios.
