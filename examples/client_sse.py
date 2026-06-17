"""Sample MCP client — SSE transport.

Connects to a running document-xml-mcp server over HTTP/SSE and exercises all four tools.
Works with any deployment target: local SSE mode, Docker single container, docker-compose
stack, self-hosted remote, or any externally accessible instance.

Usage
-----
    # Against a local SSE server (default http://localhost:8000/sse)
    uv run python examples/client_sse.py

    # Against a Docker container or remote host
    uv run python examples/client_sse.py --url http://192.168.1.100:8000/sse

    # With a DOCX file to parse
    uv run python examples/client_sse.py --docx input/CV_Test_1.docx

Starting the server (pick one)
-------------------------------
    # Option A: local SSE mode
    MCP_TRANSPORT=sse uv run document-xml-mcp

    # Option B: Docker single container
    MCP_TRANSPORT=sse docker compose up --build

    # Option C: docker-compose with n8n profile (MCP server auto-starts in SSE mode)
    MCP_TRANSPORT=sse docker compose --profile n8n up --build

Prerequisites
-------------
- The server must be running and the SSE endpoint reachable before this script starts.
- The file passed via --docx is read on THIS machine, encoded to base64, and sent to the
  server — parse_document_to_xml does not require the file to exist on the server.
- For parse_file_to_xml and parse_batch_to_xml the file or directory must exist on the
  SERVER's filesystem; those tools use server-side paths.

Server-side file paths (Docker vs local)
-----------------------------------------
parse_file_to_xml and parse_batch_to_xml operate on paths relative to the **server's**
working directory (or absolute paths on the server's filesystem).

- **Docker:** docker-compose.yml mounts the host directory ./input/ as /input inside the
  container (read-only). Pass /input/yourfile.docx as the path argument.
  Example: {"path": "/input/CV_Test_1.docx"}

- **Local (no Docker):** paths are relative to the project root, i.e. the directory where
  you run `uv run document-xml-mcp`. A file at ./input/CV_Test_1.docx is referenced as
  input/CV_Test_1.docx (or its absolute path).
"""

from __future__ import annotations

import asyncio
import base64
import json
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.sse import sse_client

DEFAULT_URL = "http://localhost:8000/sse"


def _tool_result(result) -> dict:
    """Extract and JSON-decode the first content block from a CallToolResult."""
    if result.isError:
        raise RuntimeError(f"Tool error: {result.content}")
    return json.loads(result.content[0].text)


async def demo(server_url: str, docx_path: Path | None) -> None:
    print(f"Connecting to {server_url} …")

    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(f"=== Connected to document-xml-mcp via SSE ({server_url}) ===\n")

            # ── Tool 1: list_supported_document_types ──────────────────────────
            types = _tool_result(await session.call_tool("list_supported_document_types", {}))
            print(f"Supported types : {types['supported']}")
            print(f"Planned types   : {types['planned']}")
            print()

            if docx_path is None:
                print("No --docx path supplied — pass --docx <path> to exercise parse_document_to_xml.")
                return

            if not docx_path.is_file():
                print(f"File not found: {docx_path}")
                sys.exit(1)

            # ── Tool 2: parse_document_to_xml (base64) ─────────────────────────
            # The file is read locally and sent as base64 — the server never needs
            # filesystem access for this tool.
            encoded = base64.b64encode(docx_path.read_bytes()).decode()
            resp = _tool_result(
                await session.call_tool(
                    "parse_document_to_xml",
                    {"filename": docx_path.name, "content_base64": encoded},
                )
            )
            print("parse_document_to_xml (base64 upload)")
            print(f"  paragraphs : {resp['stats']['paragraph_count']}")
            print(f"  tables     : {resp['stats']['table_count']}")
            print(f"  characters : {resp['stats']['character_count']}")
            print(f"  warnings   : {resp['warnings']}")
            print(f"  xml (first 300 chars):\n{resp['xml'][:300]}")
            print()

            # ── Tools 3 & 4 require the file on the server ─────────────────────
            print(
                "Note: parse_file_to_xml and parse_batch_to_xml require the file to exist\n"
                "      on the SERVER's filesystem inside an allowed input directory.\n"
                "      When the server is running in Docker, place files in the ./input/\n"
                "      directory (mounted as /input inside the container).\n"
            )


if __name__ == "__main__":
    url = DEFAULT_URL
    docx: Path | None = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--url" and i + 1 < len(args):
            url = args[i + 1]
            i += 2
        elif args[i] == "--docx" and i + 1 < len(args):
            docx = Path(args[i + 1])
            i += 2
        else:
            print(f"Unknown argument: {args[i]}")
            print("Usage: client_sse.py [--url URL] [--docx PATH]")
            sys.exit(1)

    asyncio.run(demo(url, docx))
