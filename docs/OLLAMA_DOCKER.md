# Connecting n8n + document-xml-mcp to Ollama

This guide covers three scenarios for providing an Ollama LLM backend to the
Docker Compose stack (`n8n` + `document-xml-mcp`).

| Scenario | Ollama location | n8n base URL |
|----------|----------------|-------------|
| [A — Host](#scenario-a--ollama-on-the-host-machine-127001) | Windows/macOS host, `127.0.0.1:11434` | `http://host.docker.internal:11434` |
| [B — On-prem](#scenario-b--on-premises-ollama-17231250211434) | Remote machine, `172.31.250.2:11434` | `http://172.31.250.2:11434` |
| [C — Containerized](#scenario-c--ollama-in-docker-with-gpu) | Docker container with GPU, host models reused | `http://ollama:11434` |

All three use **n8n's built-in Ollama credential** — no code changes needed.

**Validation endpoint used throughout:** `GET /v1/models`
(Ollama's OpenAI-compatible endpoint; available since Ollama 0.1.24.)

---

## Prerequisites

```powershell
# Confirm Docker Desktop + nvidia runtime
docker info | Select-String "Operating System|Runtimes"
```

Expected output on this machine:

```
 Operating System: Docker Desktop
 Runtimes: nvidia runc io.containerd.runc.v2
```

The `nvidia` runtime means GPU containers (Scenario C) are already supported.

---

## Scenario A — Ollama on the host machine (127.0.0.1)

Docker containers cannot reach `127.0.0.1` on the host — that address resolves to
the **container itself**. Docker Desktop (Windows and macOS) automatically provides
the DNS name `host.docker.internal` that routes to the host from inside any container.

### Why Ollama refuses Docker connections by default

Ollama on Windows binds to `127.0.0.1:11434` by default. Traffic from a Docker
container arrives from the Docker virtual network (`10.x.x.x` range), not from
`127.0.0.1`, so Ollama drops it.

### Step A1 — Allow Ollama to accept non-loopback connections

Set `OLLAMA_HOST=0.0.0.0` as a **persistent system environment variable**, then
restart Ollama:

1. Open **Windows Settings → System → Advanced system settings → Environment Variables**.
2. Under **System variables**, click **New**:
   - Variable name: `OLLAMA_HOST`
   - Variable value: `0.0.0.0`
3. Click OK on all dialogs.
4. **Right-click the Ollama system-tray icon → Quit**.
5. Reopen Ollama from the Start menu (or `Start-Process ollama`).

> **Per-session alternative (PowerShell — lost on next restart):**
>
> ```powershell
> Stop-Process -Name ollama -ErrorAction SilentlyContinue
> $env:OLLAMA_HOST = "0.0.0.0"
> Start-Process ollama
> Start-Sleep 3
> ```

**VERIFY A1 — Ollama still answers on host:**

```powershell
curl -s http://127.0.0.1:11434/v1/models | ConvertFrom-Json | Select-Object -Expand data | Select-Object id
```

Expected: list of model IDs. If empty or error → `OLLAMA_HOST` not applied, repeat Step A1.

**VERIFY A2 — Reachable from inside a Docker container:**

```powershell
docker run --rm curlimages/curl:latest curl -s http://host.docker.internal:11434/v1/models
```

Expected: same JSON. If `Connection refused` → `OLLAMA_HOST=0.0.0.0` not yet active.
If `Could not resolve host` → restart Docker Desktop.

### Step A3 — Configure n8n Ollama credential

1. Open n8n at http://localhost:5678.
2. **Settings → Credentials → Add credential → Ollama**.
3. **Base URL**: `http://host.docker.internal:11434`
4. **Save & test** — expect "Connection successful".

---

## Scenario B — On-premises Ollama (172.31.250.2:11434)

Containers can reach any IP that the host machine can route to. No special Docker
configuration is needed.

**VERIFY B1 — Reachable from the host:**

```powershell
curl -s http://172.31.250.2:11434/v1/models | ConvertFrom-Json | Select-Object -Expand data | Select-Object id
```

Expected: model list from the remote server.
If timeout/refused: the remote Ollama may not be running, or port 11434 is firewalled.

**VERIFY B2 — Reachable from inside a Docker container:**

```powershell
docker run --rm curlimages/curl:latest curl -s http://172.31.250.2:11434/v1/models
```

Expected: same list as B1.
If refused from Docker but fine from host: the remote server's `OLLAMA_HOST` is
`127.0.0.1`. Ask the admin to set it to `0.0.0.0` and restart Ollama.

### Step B3 — Configure n8n Ollama credential

Same as Scenario A Step A3, but set **Base URL** to `http://172.31.250.2:11434`.

---

## Scenario C — Ollama in Docker with GPU

The `ollama` service is defined in `docker-compose.yml` under `profiles: [ollama]`.
It mounts the host's `%USERPROFILE%\.ollama` directory so all models you have already
downloaded on the host are **instantly available** — no re-download needed.
Models pulled inside the container are also written back to the host directory.

```
%USERPROFILE%\.ollama   ←──────────────────────────────┐
                                                        │ bind mount
docker compose ollama container /root/.ollama  ─────────┘
```

Host port `11435` is used (not `11434`) to avoid conflicts with any Ollama already
running natively on the host.

### Step C1 — Confirm GPU is visible to Docker

```powershell
docker run --rm --gpus all nvidia/cuda:12.3.1-base-ubuntu22.04 nvidia-smi 2>&1 | Select-Object -First 8
```

Expected: `nvidia-smi` header table with your GPU name, driver version, CUDA version.
If "could not select device driver" → Docker Desktop → Settings → Resources → GPU → enable.

### Step C2 — Start the Ollama container

```powershell
# Start only the ollama service (no n8n or MCP server yet)
docker compose --profile ollama up -d ollama
```

Wait ~5 seconds for the process to start, then:

```powershell
docker compose logs ollama
```

Expected last line: something like `Listening on 0.0.0.0:11434 (version 0.x.y)`.

### Step C3 — Verify models are visible (the key validation)

From the **host** (port 11435):

```powershell
curl -s http://localhost:11435/v1/models | ConvertFrom-Json | Select-Object -Expand data | Select-Object id
```

From **inside the Docker network** (what n8n will use):

```powershell
docker run --rm `
  --network document-xml-mcp_default `
  curlimages/curl:latest `
  curl -s http://ollama:11434/v1/models
```

**Expected for both:** JSON array of model objects including `qwen3:8b`, `qwen3:4b-instruct`,
etc. — the same models already on the host.

If the list is empty but no error: the bind mount resolved but Ollama hasn't scanned
the directory yet — wait 10 s and retry.
If `Connection refused`: check `docker compose logs ollama` for startup errors.

### Step C4 — GPU verification inside the container

```powershell
docker compose exec ollama nvidia-smi
```

Expected: `nvidia-smi` output matching the host GPU.

### Step C5 — Start the full stack

```powershell
$env:MCP_TRANSPORT = "sse"
docker compose --profile n8n --profile ollama up --build
```

### Step C6 — Configure n8n Ollama credential

Same as Scenario A Step A3, but set **Base URL** to `http://ollama:11434`.

---

## Pulling additional models into the container

Because the container mounts `%USERPROFILE%\.ollama`, models pulled here are saved
on the host and persist across container recreations:

```powershell
# Pull a model (writes to host %USERPROFILE%\.ollama\models)
docker compose exec ollama ollama pull qwen3:8b

# Verify
docker compose exec ollama ollama list
```

---

## Choosing a model in n8n

Once the credential is saved, open the **AI Agent** node:

1. **Chat Model** → select **Ollama Chat Model**.
2. Select the credential.
3. **Model** → type or pick a model name (e.g. `qwen3:8b`).

Models with `tools` capability work best with the AI Agent + MCP Client Tool
combination. Verified tools-capable models on this machine:

| Model | Size | Capabilities |
|-------|------|-------------|
| `qwen3:8b` | 5 GB | completion, tools, thinking |
| `qwen3:4b-instruct` | 2.5 GB | completion, tools |
| `llama3.2:latest` | 2 GB | completion, tools |
| `llama3.1:8b` | 5 GB | completion, tools |
| `qwen3-coder:30b` | 19 GB | completion, tools |
| `qwen3.5:35b` | 24 GB | vision, completion, tools, thinking |
| `qwen3-coder-next:latest` | 52 GB | completion, tools |

Check any model's capabilities:

```powershell
curl -s http://127.0.0.1:11434/api/show `
  -H "Content-Type: application/json" `
  -d '{"name":"qwen3:8b"}' |
  ConvertFrom-Json | Select-Object -Expand capabilities
```

---

## Troubleshooting

| Symptom | Command to run | Fix |
|---------|---------------|-----|
| Scenario A: empty response from Docker | `VERIFY A2` | Set `OLLAMA_HOST=0.0.0.0`, restart Ollama (Step A1) |
| Scenario B: timeout from Docker | `VERIFY B2` | Check firewall on `172.31.250.2`; verify `OLLAMA_HOST` on remote |
| Scenario C: models list empty | `docker compose logs ollama` | Wait 10 s; confirm bind mount path exists |
| Scenario C: GPU not found | Step C1 | Enable GPU in Docker Desktop → Resources → GPU |
| n8n "Cannot connect to Ollama" | n8n credential test | Confirm Base URL has no trailing slash; check container is healthy |
| AI Agent ignores MCP tools | — | Ensure model has `tools` capability (see table above) |
| Container port conflict on 11435 | `netstat -ano \| findstr 11435` | Change host port in docker-compose.yml `"11436:11434"` |

---

## References

- [Ollama FAQ — OLLAMA_HOST and OLLAMA_ORIGINS](https://github.com/ollama/ollama/blob/main/docs/faq.md)
- [Ollama OpenAI-compatible API (`/v1/models`)](https://github.com/ollama/ollama/blob/main/docs/openai.md)
- [Ollama Docker Hub image](https://hub.docker.com/r/ollama/ollama)
- [NVIDIA Container Toolkit — installation guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- [Docker Desktop GPU support](https://docs.docker.com/desktop/gpu/)
- [n8n Ollama credential](https://docs.n8n.io/integrations/builtin/credentials/ollama/)
- [n8n AI Agent node](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.agent/)
