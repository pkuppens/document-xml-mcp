# n8n Integration Setup

This guide shows how to connect **document-xml-mcp** to [n8n](https://n8n.io) so that n8n
workflows can parse DOCX files and receive simplified semantic XML.

## How It Works

n8n connects to an MCP server over **HTTP/SSE transport** (not stdio).
The MCP server exposes an SSE endpoint at `http://<host>:8000/sse`.
n8n's **MCP Client Tool** node connects to that endpoint and makes all four
`document-xml-mcp` tools available to an AI Agent node inside n8n.

```
n8n AI Agent  ──(SSE)──►  document-xml-mcp :8000/sse
    │
    ├── parse_document_to_xml(filename, content_base64)
    ├── parse_file_to_xml(path)
    ├── parse_batch_to_xml(input_dir, output_dir)
    └── list_supported_document_types()
```

**Official references:**
- [n8n MCP nodes documentation](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.mcpclienttool/)
- [n8n AI Agent node](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.agent/)
- [FastMCP transports](https://gofastmcp.com/servers/running-servers#transport-options)
- [n8n Docker deployment](https://docs.n8n.io/hosting/installation/docker/)
- [MCP specification — transports](https://spec.modelcontextprotocol.io/specification/basic/transports/)

---

## Prerequisites

| Requirement | Minimum version | Notes |
|-------------|----------------|-------|
| Docker + Docker Compose | Docker 24, Compose v2 | `docker compose version` |
| n8n | 1.28.0 | First version with stable MCP Client Tool node |
| document-xml-mcp | any | This repo |

---

## Quickstart — Docker Compose

### 1. Clone and configure

```bash
git clone https://github.com/pkuppens/document-xml-mcp.git
cd document-xml-mcp
```

Set a strong encryption key for n8n credential storage (required):

```bash
# Linux / macOS / Git Bash
export N8N_ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# PowerShell
$env:N8N_ENCRYPTION_KEY = python -c "import secrets; print(secrets.token_hex(32))"
```

Or write it to a `.env` file (gitignored):

```bash
echo "N8N_ENCRYPTION_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> .env
echo "MCP_TRANSPORT=sse" >> .env
```

### 2. Start both services

```bash
# Start document-xml-mcp in SSE mode + n8n
MCP_TRANSPORT=sse docker compose --profile n8n up --build
```

- **n8n UI**: http://localhost:5678
- **MCP SSE endpoint**: http://localhost:8000/sse

### 3. First-time n8n setup

1. Open http://localhost:5678 in your browser.
2. Create an owner account (email + password — stored locally only).
3. Skip the tour or follow it briefly.

---

## Import the Example Workflow

The repository ships a ready-made workflow in `n8n/workflows/parse-document.json`.

1. In n8n, click **Workflows → Import from file**.
2. Select `n8n/workflows/parse-document.json`.
3. Open the imported workflow and configure two items:

   **a. Add an AI model credential to the AI Agent node**

   - Click the **AI Agent** node.
   - Under **Chat Model**, click **+ Add credential**.
   - Choose a provider (OpenAI, Anthropic, Ollama, etc.).
   - Paste your API key or configure the local model URL.

   **b. Verify the MCP endpoint URL**

   - Click the **document-xml-mcp** (MCP Client Tool) node.
   - Confirm **SSE Endpoint** is set to `http://document-xml-mcp:8000/sse`.
   - This Docker service name resolves correctly inside the Docker network.
   - For a locally-run MCP server (not Docker), use `http://localhost:8000/sse`.

4. Click **Save** then **Activate** the workflow.

---

## Test the Workflow

Send a POST request to the webhook:

```bash
# Linux / macOS / Git Bash — encode a DOCX file and send it
B64=$(base64 -w 0 input/CV_Test_1.docx)  # Linux
# B64=$(base64 -i input/CV_Test_1.docx | tr -d '\n')  # macOS

curl -s -X POST http://localhost:5678/webhook/parse-document \
  -H "Content-Type: application/json" \
  -d "{\"filename\": \"CV_Test_1.docx\", \"content_base64\": \"$B64\", \"prompt\": \"Parse this document to XML\"}" \
  | python -m json.tool
```

PowerShell:

```powershell
$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("input\CV_Test_1.docx"))
$body = @{ filename = "CV_Test_1.docx"; content_base64 = $b64; prompt = "Parse this document to XML" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:5678/webhook/parse-document" `
  -ContentType "application/json" -Body $body
```

Expected response:

```json
{
  "xml": "<document>\n  <body>\n    <heading level=\"1\">Jane Doe</heading>\n    ...\n  </body>\n</document>\n",
  "success": true
}
```

---

## Build Your Own Workflow

You can use any of the four MCP tools directly from an AI Agent.

### Available tools

| Tool | What it does | Required inputs |
|------|-------------|----------------|
| `parse_document_to_xml` | Parse base64-encoded DOCX bytes | `filename`, `content_base64` |
| `parse_file_to_xml` | Parse a DOCX at a server-side path | `path` (must be inside `/input`) |
| `parse_batch_to_xml` | Parse all `.docx` files in a directory | `input_dir`, `output_dir` |
| `list_supported_document_types` | Return supported formats | — |

### Node wiring pattern

```
[Trigger]  ──main──►  [AI Agent]  ──main──►  [Respond / next step]
                           │
                       ai_tool
                           │
                    [MCP Client Tool]
                    sseEndpoint: http://document-xml-mcp:8000/sse
```

The **MCP Client Tool** node connects to the agent via the `ai_tool` output port (the lower port on the node). The agent automatically discovers all available tools from the MCP server at runtime — no manual tool registration needed.

### Trigger options

| Use case | Recommended trigger |
|---------|-------------------|
| API / webhook-driven | **Webhook** node |
| Scheduled batch | **Schedule Trigger** node |
| Email attachment processing | **Gmail** or **IMAP Email** node |
| File drop | **Local File Trigger** or **FTP** node |
| Manual testing | **Manual Trigger** node |

---

## Running the MCP Server Without Docker

If you run document-xml-mcp locally (not in Docker), start it in SSE mode:

```bash
# Linux / macOS / Git Bash
MCP_TRANSPORT=sse uv run document-xml-mcp

# PowerShell
$env:MCP_TRANSPORT = "sse"
uv run document-xml-mcp
```

The server starts at `http://localhost:8000`. In n8n, set the MCP Client Tool
endpoint to `http://host.docker.internal:8000/sse` (Docker-to-host bridging on
Mac/Windows) or `http://<your-machine-ip>:8000/sse` on Linux.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Set to `sse` for HTTP/SSE mode (required for n8n) |
| `MCP_HOST` | `0.0.0.0` | Bind address for SSE server |
| `MCP_PORT` | `8000` | Bind port for SSE server |

---

## Production Considerations

> **Note:** The setup above is suitable for local development and private-network
> deployments. For production, apply the following hardening steps.

### TLS / HTTPS

n8n's SSE nodes work over HTTPS once you put a reverse proxy in front of the
MCP server. Using nginx:

```nginx
location /mcp/ {
    proxy_pass http://document-xml-mcp:8000/;
    proxy_http_version 1.1;
    # Required for SSE: disable buffering
    proxy_buffering off;
    chunked_transfer_encoding off;
    proxy_read_timeout 3600s;
    proxy_set_header Connection '';
}
```

Reference: [nginx SSE proxy configuration](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_buffering)

### Authentication

The current MCP server has no authentication. For a networked deployment:
- Place the MCP server behind nginx with HTTP Basic Auth or mTLS.
- Or restrict access to a private Docker network and expose only n8n externally.

### n8n credential storage

n8n stores credentials encrypted with `N8N_ENCRYPTION_KEY`. Keep this key in a
secrets manager (Vault, AWS Secrets Manager, etc.) and never commit it.

Reference: [n8n environment variables — security](https://docs.n8n.io/hosting/configuration/environment-variables/security/)

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| MCP Client Tool shows "Connection refused" | MCP server not in SSE mode | Set `MCP_TRANSPORT=sse` and restart |
| MCP Client Tool shows "Connection refused" from Docker | Wrong hostname | Use `http://document-xml-mcp:8000/sse` (Docker service name), not `localhost` |
| AI Agent doesn't call any tool | No tools discovered | Check that the SSE endpoint is reachable; view server logs with `docker compose logs document-xml-mcp` |
| `parse_file_to_xml` returns "not within any allowed directory" | Path outside `/input` | Copy file to `./input/` on the host; it mounts to `/input` in the container |
| n8n UI not loading | Port conflict | Change `5678:5678` mapping in docker-compose.yml |
| Server crashes immediately in SSE mode | Missing `uvicorn` / `starlette` dependency | These ship with `mcp[cli]`; run `uv sync` to ensure deps are current |

### View logs

```bash
# All services
docker compose --profile n8n logs -f

# MCP server only
docker compose logs -f document-xml-mcp

# n8n only
docker compose --profile n8n logs -f n8n
```
