"""Sample MCP client — stdio transport.

Spawns document-xml-mcp as a child process and exercises all tools, prompts, and resources.

Usage
-----
    # List supported types and show prompts/resources only
    uv run python examples/client_stdio.py

    # Full demo: parse a local DOCX file and extract CV fields
    uv run python examples/client_stdio.py --docx input/CV_Test_1.docx

Prerequisites
-------------
- `uv` on PATH (the server is launched via `uv run document-xml-mcp`)
- The package installed in the project venv (`uv sync`)

When running parse_file_to_xml and parse_batch_to_xml the file's parent directory
is added to the server's allowed-input-dirs list so the tool can access it.
"""

from __future__ import annotations

import asyncio
import base64
import json
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def _tool_result(result) -> dict:
    """Extract and JSON-decode the first content block from a CallToolResult."""
    if result.isError:
        raise RuntimeError(f"Tool error: {result.content}")
    return json.loads(result.content[0].text)


async def demo(docx_path: Path | None) -> None:
    input_dir = str(docx_path.parent.resolve()) if docx_path else str(Path("input").resolve())

    server_params = StdioServerParameters(
        command="uv",
        args=["run", "document-xml-mcp"],
        env={
            # Comma-separated paths or JSON arrays are both accepted.
            "XML_PROCESSING_ALLOWED_INPUT_DIRS": input_dir,
            "XML_PROCESSING_ALLOWED_OUTPUT_DIRS": input_dir,
            "XML_PROCESSING_LOG_LEVEL": "WARNING",
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("=== Connected to document-xml-mcp via stdio ===\n")

            # ── Tool: list_supported_document_types ────────────────────────────
            types = _tool_result(await session.call_tool("list_supported_document_types", {}))
            print(f"Supported types : {types['supported']}")
            print(f"Planned types   : {types['planned']}")
            print()

            # ── Prompts: list and retrieve ─────────────────────────────────────
            # MCP prompts are instruction templates the LLM client applies.
            # The server returns the template; the LLM executes it.
            prompts_result = await session.list_prompts()
            print(f"Available prompts ({len(prompts_result.prompts)}):")
            for p in prompts_result.prompts:
                args = [a.name for a in (p.arguments or [])]
                print(f"  {p.name}({', '.join(args)}) — {p.description}")
            print()

            # Retrieve one prompt to show the template content
            sample_cv_xml = "<document><body><heading level='1'>Jane Doe</heading></body></document>"
            sample_job = "Senior Data Engineer. Requirements: Python, Spark, 5+ years."
            prompt_result = await session.get_prompt(
                "analyze_cv_gaps",
                {"cv_xml": sample_cv_xml, "job_description": sample_job},
            )
            print("Sample prompt retrieval — analyze_cv_gaps:")
            for msg in prompt_result.messages:
                preview = str(msg.content)[:200].replace("\n", " ")
                print(f"  role={msg.role} content={preview}...")
            print()

            # ── Resources: list and read ───────────────────────────────────────
            # MCP resources are data the LLM reads as context (schemas, templates).
            resources_result = await session.list_resources()
            print(f"Available resources ({len(resources_result.resources)}):")
            for r in resources_result.resources:
                print(f"  {r.uri} ({r.mimeType}) — {r.description}")
            print()

            # Read the CV export schema resource
            schema_result = await session.read_resource("cv://templates/export-schema")
            schema_text = schema_result.contents[0].text if schema_result.contents else ""
            print("Resource cv://templates/export-schema (first 300 chars):")
            print(f"  {schema_text[:300].replace(chr(10), ' ')}")
            print()

            if docx_path is None:
                print("No --docx path supplied — pass --docx <path> to exercise parse tools.")
                return

            if not docx_path.is_file():
                print(f"File not found: {docx_path}")
                sys.exit(1)

            # ── Tool: parse_document_to_xml (base64) ──────────────────────────
            encoded = base64.b64encode(docx_path.read_bytes()).decode()
            resp = _tool_result(
                await session.call_tool(
                    "parse_document_to_xml",
                    {"filename": docx_path.name, "content_base64": encoded},
                )
            )
            print("parse_document_to_xml")
            print(f"  paragraphs : {resp['stats']['paragraph_count']}")
            print(f"  tables     : {resp['stats']['table_count']}")
            print(f"  xml (first 300 chars):\n{resp['xml'][:300]}")
            print()
            cv_xml = resp["xml"]

            # ── Tool: parse_file_to_xml ────────────────────────────────────────
            resp = _tool_result(
                await session.call_tool(
                    "parse_file_to_xml",
                    {"path": str(docx_path.resolve())},
                )
            )
            print("parse_file_to_xml")
            print(f"  paragraphs : {resp['stats']['paragraph_count']}")
            print(f"  warnings   : {resp['warnings']}")
            print()

            # ── Tool: extract_cv_fields ────────────────────────────────────────
            fields = _tool_result(await session.call_tool("extract_cv_fields", {"xml": cv_xml}))
            print("extract_cv_fields")
            print(f"  name       : {fields.get('name')}")
            print(f"  email      : {fields['contact'].get('email')}")
            print(f"  skills     : {fields.get('skills', [])[:5]}")
            print(f"  experience : {len(fields.get('experience', []))} entries")
            print(f"  warnings   : {fields.get('warnings', [])}")
            print()

            # ── Tool: parse_batch_to_xml ───────────────────────────────────────
            resp = _tool_result(
                await session.call_tool(
                    "parse_batch_to_xml",
                    {
                        "input_dir": input_dir,
                        "output_dir": input_dir,
                        "continue_on_error": True,
                    },
                )
            )
            print("parse_batch_to_xml")
            print(f"  processed : {resp['processed']}")
            print(f"  failed    : {resp['failed']}")
            for r in resp["results"]:
                status = "OK" if r["error"] is None else f"FAIL: {r['error']}"
                print(f"  {r['filename']} -> {status}")


if __name__ == "__main__":
    docx: Path | None = None
    if "--docx" in sys.argv:
        idx = sys.argv.index("--docx")
        if idx + 1 >= len(sys.argv):
            print("Usage: client_stdio.py [--docx PATH]")
            sys.exit(1)
        docx = Path(sys.argv[idx + 1])

    asyncio.run(demo(docx))
