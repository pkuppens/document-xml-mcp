"""MCP server entrypoint."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("document-xml-mcp")


@mcp.tool()
def list_supported_document_types() -> dict:
    """Return currently supported and planned document types."""
    return {"supported": ["docx"], "planned": ["pdf", "html", "markdown", "odt"]}


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
