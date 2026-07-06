# PocketAgent MCP Server

The PocketAgent MCP (Model Context Protocol) server exposes **51 tools**, **5
resources**, and **4 prompts** over stdio, so any MCP-compatible client —
Claude Desktop, Codex, Cursor, etc. — can drive Pocket Network's decentralized
RPC across 52 chains directly.

> One MCP server. 52 chains. Zero centralized RPC. Powered by Pocket Network.

## Why an MCP server?

BlockchainQuery (the PNF official MCP server, v2.1.2) is a Node.js MCP server
distributed as a Claude Desktop Extension. It can't be imported into a Python
backend, and it's **read-only**. PocketAgent reimplements its 32-tool read
surface directly against Pocket Network RPC (via the protocol dispatcher in
`pocket_rpc.py`) and adds **19 custom tools** — compare, guarded native writes
for EVM/Solana/Tron/Cosmos/Sui/NEAR, non-EVM token transfers
(SPL/TRC-20/CW20/IBC/NEP-141/SUI coin), analytics, POKT cost, compositional
wallet analysis, and simulation — that BlockchainQuery does not provide. The
MCP server makes all of this available to any AI client, not just PocketAgent's
own chat UI.

## Architecture: single-layer adapter

The MCP server is a **thin adapter** over `backend/tools/TOOL_REGISTRY`. All
51 tools are already implemented there with executors, and the chat UI calls
them via `execute_tool(name, ToolContext, args)`. The MCP server does **not**
re-route tools — `call_tool` delegates to the same `execute_tool`. This keeps
the tool surface identical across chat and MCP with zero routing drift.

```
MCP client (Claude Desktop / Codex)
        │  stdio
        ▼
┌─────────────────────────────┐
│  mcp_server/server.py       │  list_tools / call_tool / resources / prompts
│  (thin adapter)             │
└──────────┬──────────────────┘
           │ execute_tool(name, context, args)
           ▼
┌─────────────────────────────┐
│  backend/tools/             │  51 tools (32 read + 19 custom), already built
│  TOOL_REGISTRY              │
└──────────┬──────────────────┘
           │ reads via protocol dispatcher
           ▼
┌─────────────────────────────┐
│  services/pocket_rpc.py     │  EVM / Solana / Cosmos / Sui / Near / Tron
│  → Pocket Network RPC       │  52 chains, cached + backoff
└─────────────────────────────┘
```

## Install & run

### pip install (recommended)

```bash
pip install pocketagent
```

After install, the `pocketagent-mcp` command is available in your PATH.

### From source

```bash
git clone https://github.com/Jayanng/PocketAgent.git
pip install ./PocketAgent/backend
```

### From source

The `mcp` SDK is already in `backend/requirements.txt` (`mcp>=1.28.0`).

```bash
cd backend
python -m pocketagent.mcp_server.server        # stdio server, blocks until client disconnects
# or, from the repo root:
python -m backend.mcp_server.server
```

The server speaks MCP over stdio. It is designed to be launched **by** an MCP
client (which spawns it as a subprocess), not run manually — see the client
configs below.

`DATABASE_PATH` may be absolute or relative. When installed via pip, set an absolute
path or let the server use its default (`./data/pocketagent.db` relative to the
working directory of the MCP client).

## Configure with Claude Desktop

Add to `claude_desktop_config.json` (macOS:
`~/Library/Application Support/Claude/claude_desktop_config.json`; Windows:
`%APPDATA%\Claude\claude_desktop_config.json`):

**If installed via pip:**

```jsonc
{
  "mcpServers": {
    "pocketagent": {
      "command": "pocketagent-mcp",
      "env": {
        "DATABASE_PATH": "./data/pocketagent.db",
        "ENCRYPTION_KEY": "<your-32-byte-key>",
        "OPENAI_API_KEY": "<your-openai-api-key>"
      }
    }
  }
}
```

**If running from source:**

```jsonc
{
  "mcpServers": {
    "pocketagent": {
      "command": "python",
      "args": ["-m", "backend.mcp_server.server"],
      "cwd": "C:/Users/dell/Documents/VS_code/PocketAgent",
      "env": {
        "DATABASE_PATH": "./data/pocketagent.db",
        "ENCRYPTION_KEY": "<your-32-byte-key>",
        "OPENAI_API_KEY": "<your-openai-api-key>"
      }
    }
  }
}
```

After saving, restart Claude Desktop. The `pocketagent` server appears under
**Settings → Developer**, and all 51 tools, 5 resources, and 4 prompts become
available to Claude.

## Configure with Codex / Codex CLI

Add to your Codex `config.toml` (or the equivalent `settings.json` your Codex
build reads):

**If installed via pip:**

```toml
[mcp_servers.pocketagent]
command = "pocketagent-mcp"

[mcp_servers.pocketagent.env]
DATABASE_PATH = "./data/pocketagent.db"
ENCRYPTION_KEY = "<your-32-byte-key>"
OPENAI_API_KEY = "<your-openai-api-key>"
```

**If running from source:**

```toml
[mcp_servers.pocketagent]
command = "python"
args = ["-m", "backend.mcp_server.server"]
cwd = "C:/Users/dell/Documents/VS_code/PocketAgent"

[mcp_servers.pocketagent.env]
DATABASE_PATH = "./data/pocketagent.db"
ENCRYPTION_KEY = "<your-32-byte-key>"
OPENAI_API_KEY = "<your-openai-api-key>"
```

For a JSON-style Codex config (`settings.json`):

**If installed via pip:**

```json
{
  "mcpServers": {
    "pocketagent": {
      "command": "pocketagent-mcp",
      "env": { "DATABASE_PATH": "./data/pocketagent.db", "ENCRYPTION_KEY": "<key>", "OPENAI_API_KEY": "<key>" }
    }
  }
}
```

**If running from source:**

```json
{
  "mcpServers": {
    "pocketagent": {
      "command": "python",
      "args": ["-m", "backend.mcp_server.server"],
      "cwd": "C:/Users/dell/Documents/VS_code/PocketAgent",
      "env": { "DATABASE_PATH": "./data/pocketagent.db", "ENCRYPTION_KEY": "<key>", "OPENAI_API_KEY": "<key>" }
    }
  }
}
```

> Tip: for a live AI→blockchain demo, point Codex or Claude Desktop at the
> server and ask: *"Use the analyze_wallet tool on 0xd8dA… across ethereum,
> polygon, and arbitrum, then tell me the total USD value."*

## Tools (51 total)

All tools return JSON text. Reads are protocol-dispatched (EVM/Solana/Cosmos/
Sui/Near/Tron) and enriched with USD values where possible. Write tools
(`send_transaction`, `send_erc20`, `contract_call`, `simulate_transaction`)
require an `agent_id` argument. Live native transfer signing and broadcast are
enabled for EVM, Solana, Tron, Cosmos (12 app-chains), Sui, and NEAR. ERC-20
and contract writes are EVM-only.

### Read — 32 tools (mirror BlockchainQuery's surface)

**Generic (2)**
- `list_chains` — list PocketAgent-supported chains, optionally filtered by protocol family
- `get_chain_info` — chain metadata: protocol, RPC URL, symbol, decimals, explorer

**EVM (9)**
- `evm_get_balance`, `evm_get_block`, `evm_get_transaction`, `evm_get_receipt`,
  `evm_get_logs`, `evm_estimate_gas`, `evm_get_token_info`, `evm_call_contract`,
  `evm_call`

**Solana (5)** — `solana_get_balance`, `solana_get_account`, `solana_get_block`,
`solana_get_transaction`, `solana_get_signatures`

**Cosmos (6)** — `cosmos_get_balance`, `cosmos_get_staking`, `cosmos_get_validators`,
`cosmos_get_transaction`, `cosmos_get_governance`, `cosmos_get_block`

**Sui (4)** — `sui_get_balance`, `sui_get_object`, `sui_get_transaction`, `sui_get_coins`

**Near (3)** — `near_query`, `near_get_block`, `near_get_transaction`

**Cross (3)** — `resolve_domain`, `compare_balances`, `convert_units`

### Compare — 3 tools
- `compare_chains` — gas prices, block times, health across chains
- `recommend_chain` — ranked best chain for an operation type
- `estimate_transaction_cost` — gas + token cost before executing

### Write — 9 tools (require `agent_id`)
- `send_transaction` — native transfers on EVM, Solana, Tron, Cosmos, Sui, and NEAR
- `send_erc20` — ERC-20 transfer on EVM only
- `contract_call` — read/write contract calls on EVM, Solana, Cosmos (CosmWasm), SUI (Move), NEAR, and Tron
- `send_trc20_token` — TRC-20 token transfer on Tron
- `send_spl_token` — SPL token transfer on Solana
- `send_ibc_token` — IBC-denom token transfer on Cosmos chains
- `send_cw20_token` — CW20 (CosmWasm) token transfer on Cosmos chains
- `send_sui_token` — non-SUI coin type transfer on SUI
- `send_nep141_token` — NEP-141 (NEAR fungible token) transfer

### Analytics — 3 tools
- `get_relay_stats`, `get_relay_history`, `get_cost_breakdown`

### POKT — 1 tool
- `estimate_relay_cost` — notional POKT cost of an operation before running it

### Compositional — 1 tool
- `analyze_wallet` — chains 5+ read queries into one wallet report

### Simulation — 1 tool
- `simulate_transaction` — dry-run a tx before broadcasting (EVM/Solana/Tron/Cosmos/Sui/NEAR)

## Resources (5)

Resources are read-only context a client can pull (unlike tools, which act).

| URI | Name | Description |
|-----|------|-------------|
| `pocket://chains` | Supported Chains | All chains with metadata |
| `pocket://chains/{chain}/status` | Chain Status | Live block height + health via Pocket RPC |
| `pocket://agents/{agent_id}/stats` | Agent Stats | Relay statistics for an agent |
| `pocket://agents/{agent_id}/wallet` | Agent Wallet | Agent wallet context |
| `pocket://cache/stats` | Cache Stats | Cache hit/miss + relays saved |

## Prompts (4)

Pre-built prompt templates that scaffold common multi-chain tasks.

| Prompt | Required args | Optional args |
|--------|---------------|---------------|
| `analyze_wallet` | `address` | — |
| `find_cheapest_chain` | `operation_type` | — |
| `track_pokt_costs` | `agent_id` | — |
| `compare_and_recommend` | `chains` | `operation_type` |

## How caching reduces POKT relay consumption

The `PocketRPCClient` holds a two-tier `ResponseCache` (`services/cache.py`):
immutable blocks/receipts/transactions/chain-ids are cached forever; balances
get a 5-minute TTL, gas prices 30 seconds. **Every cache hit is a relay we did
not make** — pull `pocket://cache/stats` to see hits, misses, and the
estimated POKT saved. `relay_cost_pokt` is a *notional* estimate (relay count
× `NOTIONAL_POKT_PER_RELAY`); the public Pocket portal costs users zero POKT.

## Human-readable output & event decoding

Tool results pass through `services/output_formatter.py`, which converts raw
protocol values into human-readable form with USD enrichment: wei →
`"1.5 ETH ($5,700)"`, lamports → `"100 SOL ($15,000)"`, etc. Transaction
receipts are enriched by `services/event_decoder.py`, which decodes known
event signatures (Transfer, Approval, Swap, …) into
`{"event": "Transfer", "from": "0x…", "to": "0x…", "value": "100 USDC"}`.

## Live AI → blockchain demo

1. Start the backend API (`uvicorn backend.main:app`) so the DB + relay logs exist.
2. Create + fund an agent (via the `/agents` API or the chat UI's agent creator).
3. Point Claude Desktop / Codex at this MCP server (configs above).
4. Ask the AI: *"Analyze wallet 0xd8dA… across ethereum, polygon, and
   arbitrum, find the cheapest EVM chain for a native transfer, and send 0.01
   ETH on the recommended chain using agent <agent_id>."* — the AI will call
   `analyze_wallet` → `recommend_chain` → `estimate_transaction_cost` →
   `send_transaction`, signing with the agent wallet via Pocket RPC.

## Testing

```bash
cd backend
python -m pytest tests/test_prompt13_mcp_server.py -v
```

The suite (21 tests) is hermetic: the module-level rpc/tracker are faked so no
Pocket RPC, CoinGecko, or live network is hit. The `agent_id` transact path
uses a temp sqlite DB with a seeded agent.