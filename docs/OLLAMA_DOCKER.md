# Connecting n8n + document-xml-mcp to Ollama

This guide covers three scenarios for providing an Ollama LLM backend to the
Docker Compose stack (`n8n` + `document-xml-mcp`).

| Scenario | Ollama location | n8n base URL |
|----------|----------------|-------------|
| [A — Host](#scenario-a--ollama-on-the-host-machine-127001) | Windows/macOS host, `127.0.0.1:11434` | `http://host.docker.internal:11434` |
| [B — On-prem](#scenario-b--on-premises-ollama-17231250211434) | Remote machine, `172.31.250.2:11434` | `http://172.31.250.2:11434` |
| [C — Containerized](#scenario-c--ollama-in-docker-with-gpu) | Docker container with GPU | `http://ollama:11434` |

All three use **n8n's built-in Ollama credential** — no code changes needed.

---

## Prerequisites

### Docker runtime info (run once, paste result)

```powershell
docker info | Select-String "Operating System|Runtimes"
```

Expected for this machine:

```
 Operating System: Docker Desktop
 Runtimes: nvidia runc io.containerd.runc.v2
```

The `nvidia` runtime being listed means GPU containers (Scenario C) are already
supported by your Docker Desktop installation.

---

## Scenario A — Ollama on the host machine (127.0.0.1)

Docker containers cannot reach `127.0.0.1` on the host directly — that address
resolves to the container itself. Docker Desktop (Windows and macOS) automatically
provides `host.docker.internal` as a stable DNS name that routes to the host.

### Why this matters

Ollama on Windows listens on `127.0.0.1:11434` by default. Traffic from a Docker
container arrives from the Docker virtual network (`10.x.x.x` or similar), not from
`127.0.0.1`. Ollama will **refuse** the connection unless told to accept it.

### Step A1 — Allow Ollama to accept connections from Docker

Set `OLLAMA_HOST=0.0.0.0` so Ollama binds to all interfaces:

1. Open **Windows Settings → System → Advanced system settings → Environment Variables**.
2. Under **System variables**, click **New**:
   - Variable name: `OLLAMA_HOST`
   - Variable value: `0.0.0.0`
3. Click OK, then **right-click the Ollama system-tray icon → Quit**.
4. Reopen Ollama from the Start menu.

> **Alternative (PowerShell, per-session only):**
>
> ```powershell
> $env:OLLAMA_HOST = "0.0.0.0"
> ollama serve
> ```

**Verify — run this and paste the output:**

```powershell
# Should still return your model list (Ollama still works normally)
curl -s http://127.0.0.1:11434/api/tags | ConvertFrom-Json | Select-Object -Expand models | Select-Object name
```

### Step A2 — Confirm `host.docker.internal` resolves from a container

```powershell
docker run --rm curlimages/curl:latest `
  curl -s http://host.docker.internal:11434/api/tags
```

**Expected:** JSON list of models (same as Step A1).  
**If you get "Connection refused":** `OLLAMA_HOST=0.0.0.0` was not applied — repeat Step A1.  
**If you get "Could not resolve host":** Docker Desktop may need a restart.

### Step A3 — Configure n8n Ollama credential

1. Open n8n at http://localhost:5678.
2. Go to **Settings → Credentials → Add credential → Ollama**.
3. Set **Base URL**: `http://host.docker.internal:11434`
4. Click **Save & test** — you should see "Connection successful".
5. In your AI Agent node, select this credential and choose a model (e.g. `qwen3:8b`).

---

## Scenario B — On-premises Ollama (172.31.250.2:11434)

Docker containers can route to arbitrary IPs that the host machine can reach.
No special Docker configuration is needed — n8n simply connects to the remote IP.

### Step B1 — Verify the on-prem Ollama is reachable from the host

```powershell
curl -s http://172.31.250.2:11434/api/tags | ConvertFrom-Json | Select-Object -Expand models | Select-Object name
```

**Expected:** list of models available on that server.  
**If timeout/refused:** the on-prem Ollama may not be running, or a firewall is blocking port 11434.

### Step B2 — Verify reachability from inside a Docker container

```powershell
docker run --rm curlimages/curl:latest `
  curl -s http://172.31.250.2:11434/api/tags
```

**Expected:** same model list as Step B1.  
**If refused from Docker but fine from host:** the on-prem server's `OLLAMA_HOST` may be set to `127.0.0.1`. Ask the admin to set it to `0.0.0.0`.

### Step B3 — Configure n8n Ollama credential

Same as Scenario A, Step A3, but use:

- **Base URL**: `http://172.31.250.2:11434`

---

## Scenario C — Ollama in Docker with GPU

This adds an `ollama` container to the Compose stack. The container gets direct
GPU access through Docker Desktop's NVIDIA integration.

### Prerequisites for GPU containers

Your `docker info` output already shows `nvidia` in Runtimes, which means the
**NVIDIA Container Toolkit** is installed. Confirm GPU is visible:

```powershell
# Should show your GPU
docker run --rm --gpus all nvidia/cuda:12.3.1-base-ubuntu22.04 nvidia-smi
```

**Expected:** `nvidia-smi` table showing your GPU name, driver version, CUDA version.  
**If "could not select device driver":** enable GPU in Docker Desktop → Settings → Resources → GPU.

### docker-compose.yml already includes the `ollama` profile

The `docker-compose.yml` in this repo has an `ollama` profile ready to use.
Start the full stack with GPU Ollama:

```powershell
# Windows PowerShell
$env:MCP_TRANSPORT = "sse"
docker compose --profile n8n --profile ollama up --build
```

```bash
# Git Bash / Linux / macOS
MCP_TRANSPORT=sse docker compose --profile n8n --profile ollama up --build
```

### Step C1 — Pull a model into the Ollama container

The container starts empty. Pull a model (this downloads into the `ollama_data` volume):

```powershell
# Pull qwen3:8b (5 GB) — adjust to any model you prefer
docker compose exec ollama ollama pull qwen3:8b
```

List available models in the container:

```powershell
docker compose exec ollama ollama list
```

### Step C2 — Verify the container is reachable

```powershell
docker compose exec n8n wget -qO- http://ollama:11434/api/tags
```

**Expected:** JSON with the models pulled in Step C1.  
(The hostname `ollama` resolves because both services share the default Compose network.)

### Step C3 — Configure n8n Ollama credential

Same as Scenario A, Step A3, but use:

- **Base URL**: `http://ollama:11434`

### GPU verification inside the container

```powershell
docker compose exec ollama nvidia-smi
```

**Expected:** `nvidia-smi` output matching your host GPU.

---

## Choosing a model in n8n

Once the credential is saved and tested, open the **AI Agent** node:

1. Under **Chat Model**, select **Ollama Chat Model**.
2. Select the credential you created.
3. In **Model**, type or select a model name (e.g. `qwen3:8b`).

Models that support `tools` capability work best with the AI Agent + MCP Client Tool
combination. From your local Ollama, the following models have `tools` support:

| Model | Size | Notes |
|-------|------|-------|
| `qwen3:8b` | 5 GB | Good balance of speed and quality |
| `qwen3:4b-instruct` | 2.5 GB | Fastest; lighter on RAM |
| `llama3.2:latest` | 2 GB | Meta's 3B model |
| `llama3.1:8b` | 5 GB | Solid general-purpose |
| `qwen3-coder:30b` | 19 GB | Strong at structured output |
| `qwen3.5:35b` | 24 GB | High quality, needs 32+ GB VRAM or RAM |

Verify a model's capabilities:

```powershell
# Returns capabilities list including "tools" if supported
curl -s http://127.0.0.1:11434/api/show -d '{"name":"qwen3:8b"}' |
  ConvertFrom-Json | Select-Object -Expand capabilities
```

---

## Troubleshooting

| Symptom | Check | Fix |
|---------|-------|-----|
| n8n "Connection refused" to host Ollama | Step A2 | Set `OLLAMA_HOST=0.0.0.0`, restart Ollama |
| n8n "Connection refused" to on-prem | Step B2 | Check firewall on `172.31.250.2`; verify `OLLAMA_HOST` on that server |
| GPU container exits immediately | Step C prereq | Enable GPU in Docker Desktop settings |
| Ollama container starts but model not found | Step C1 | `docker compose exec ollama ollama pull <model>` |
| AI Agent doesn't call MCP tools | — | Ensure model has `tools` capability (see table above) |
| `nvidia-smi` not found in container | — | Use `ollama/ollama` image, not bare `nvidia/cuda` |

---

## References

- [Ollama environment variables](https://github.com/ollama/ollama/blob/main/docs/faq.md#how-do-i-configure-ollama-server) — `OLLAMA_HOST`, `OLLAMA_ORIGINS`, etc.
- [NVIDIA Container Toolkit installation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- [Docker Desktop GPU support](https://docs.docker.com/desktop/gpu/)
- [Ollama Docker Hub image](https://hub.docker.com/r/ollama/ollama)
- [n8n Ollama credential docs](https://docs.n8n.io/integrations/builtin/credentials/ollama/)
- [n8n AI Agent node](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.agent/)
