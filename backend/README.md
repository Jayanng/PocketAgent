# pokt-agent-mcp

**MCP server for 52 blockchains via [Pocket Network](https://www.pokt.network/) decentralized RPC.**

Install the package to add PocketAgent's 51 blockchain tools, 5 resources, and 4 prompts to Claude Desktop, Cursor, Codex, or any MCP stdio client.

## Install

```bash
pip install pokt-agent-mcp
```

Optional REST API dependencies (FastAPI + Uvicorn):

```bash
pip install "pokt-agent-mcp[api]"
```

## Run

After install, MCP clients should launch the console script (stdio):

```bash
pocketagent-mcp
```

Equivalent module invocation:

```bash
python -m pocketagent.mcp_server.server
```

## Claude Desktop / Cursor config

```json
{
  "mcpServers": {
    "pocketagent": {
      "command": "pocketagent-mcp",
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "ENCRYPTION_KEY": "...",
        "JWT_SECRET": "..."
      }
    }
  }
}
```

## Full platform

This package ships the **MCP server and tool layer**. The full PocketAgent platform (Next.js UI, agent management, chat) lives in the [PocketAgent repository](https://github.com/Jayanng/PocketAgent).

Documentation: [docs/mcp-server.md](https://github.com/Jayanng/PocketAgent/blob/main/docs/mcp-server.md)