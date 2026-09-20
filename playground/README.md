# Playground — dummy vibration lab

English code, Korean teaching docs.

```text
dummy-sensor → Mosquitto :1883 → mcp-server :8000 → Open WebUI :8080
```

## Quick start

```bash
cp .env.example .env   # add your free-tier key
./scripts/up.sh
curl -s http://localhost:8000/health
# Open http://localhost:8080
./scripts/down.sh
```

Student steps: [`docs/STUDENT.md`](../docs/STUDENT.md)  
Markdown skill: [`skills/vibration-pdm.md`](skills/vibration-pdm.md)

## Tools on the MCP server

| Tool | Purpose |
| --- | --- |
| `list_sensors` | Catalog + last status |
| `get_vibration_reading` | Latest reading for one id |
| `get_recent_anomalies` | Recent threshold breaches |

Inspect without an LLM: `GET /health`, `GET /demo/sensors`, `GET /demo/anomalies`.

Open WebUI native MCP expects **Streamable HTTP** at `http://mcp-server:8000/mcp` (from the UI container) with auth type **None**.
