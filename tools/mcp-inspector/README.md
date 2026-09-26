# MCP Inspector (cooking website)

[Official MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) wired for this repo. Uses **`MCP_API_KEY`** (same as Cursor CLI) to test Streamable HTTP through your full nginx chain.

**Requires:** Node.js **22.19+** recommended (`@modelcontextprotocol/inspector` engine); Node 20 may work with warnings. Network access to the MCP URL (run on your laptop for prod homelab).

## Quick start

From the repo root:

```bash
./scripts/mcp-inspector.sh          # web UI
./scripts/mcp-inspector.sh probe    # automated checks (HEAD, OAuth metadata, initialize, tools/list, ping)
./scripts/mcp-inspector.sh cli --method tools/list
./scripts/mcp-inspector.sh config-cli cooking-local --method tools/list
```

Reads **`PUBLIC_BASE_URL`** and **`MCP_API_KEY`** from `.env` at the repo root. Override URL:

```bash
MCP_INSPECTOR_URL=https://www.homelabdu204.ca/recipes/mcp/ ./scripts/mcp-inspector.sh probe
```

## Config file

`mcp.json` lists **cooking-local** and **cooking-homelab** URLs (no secrets). The script passes `Authorization: Bearer …` via `--header`; do not commit API keys into JSON.

Spark OAuth is not exercised here — use Connected Apps in Gemini for that path.
