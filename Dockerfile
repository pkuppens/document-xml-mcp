FROM python:3.12-slim

RUN pip install uv --no-cache-dir

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN uv sync --no-dev

RUN useradd --no-create-home --shell /bin/false appuser
USER appuser

CMD ["uv", "run", "document-xml-mcp"]
