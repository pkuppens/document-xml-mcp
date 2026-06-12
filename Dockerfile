FROM python:3.12-slim

RUN pip install uv --no-cache-dir

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

RUN uv sync --no-dev --frozen

RUN useradd --no-create-home --shell /bin/false appuser
USER appuser

# SSE transport port (only used when MCP_TRANSPORT=sse)
EXPOSE 8000

CMD ["uv", "run", "document-xml-mcp"]
