<h1 align="center">PocketAgent</h1>

<p align="center">
  <strong>AI agents that reason about and interact with 52 blockchains — through natural language.</strong><br/>
  <em>Powered by <a href="https://www.pokt.network/">Pocket Network</a> — decentralized RPC, no API keys required.</em>
</p>

<p align="center">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue">
  <img alt="Python" src="https://img.shields.io/badge/python-3.11+-blue?logo=python">
  <img alt="TypeScript" src="https://img.shields.io/badge/typescript-strict-blue?logo=typescript">
  <img alt="Tests" src="https://img.shields.io/badge/tests-252%20passing-brightgreen">
  <img alt="Chains" src="https://img.shields.io/badge/chains-52-orange">
  <img alt="MCP Tools" src="https://img.shields.io/badge/mcp%20tools-51-purple">
</p>

---

## What is PocketAgent?

PocketAgent is a full-stack platform where **AI agents orchestrate blockchain operations across 52 chains**. You create an agent, give it spending caps and capabilities, fund its wallet, and then talk to it — or schedule **Automations** that re-run the same prompts on a timer without opening chat. Ask it to compare gas fees across networks, analyze your portfolio, simulate a transaction, or send tokens — the agent picks the right tools, reads the chain state, and executes.

Every request flows through Pocket Network's decentralized Shannon gateway. That means no Infura, no Alchemy, no centralized API keys. Just open, permissionless RPC.

The platform ships with a **polished chat UI**, **Automations** (recurring agent jobs), a **REST API** with auto-generated OpenAPI docs, and a standalone **MCP server** that drops directly into Claude Desktop, Cursor, or Codex.

---

## How It Works

```
  CREATE AGENT      FUND WALLET       CHAT / AUTOMATE      EXECUTE            MONITOR
 ┌────────────┐    ┌────────────┐    ┌──────────────┐    ┌────────────┐    ┌────────────┐
 │ Name it     │    │ Deposit    │    │ Chat now, or │    │ Cap check  │    │ Relays     │
 │ Tool caps   │───▶│ ETH, SOL,  │───▶│ schedule a   │───▶│ Balance    │───▶│ Health     │
 │ Spend caps  │    │ USDC, …    │    │ recurring    │    │ Broadcast  │    │ Costs      │
 │ Enc. keys   │    │            │    │ prompt       │    │ SSE tx     │    │ Portfolio  │
 └────────────┘    └────────────┘    └──────────────┘    └────────────┘    └────────────┘
```

**Step 1 — Create** &nbsp; Name your agent, pick which blockchain capabilities to enable, and set per-chain spending caps. The platform generates encrypted multi-chain wallet keys (EVM, Solana, SUI, NEAR, Cosmos, TRON) and issues protected access tokens.

**Step 2 — Fund** &nbsp; Deposit native tokens or ERC-20 / SPL / TRC-20 / CW20 / NEP-141 / SUI tokens to the agent's addresses. The dashboard shows live balances across all chains.

**Step 3 — Chat or Automate** &nbsp; Ask anything in natural language, or open **Automations** and schedule a prompt (gas checks, portfolio summaries, balance monitors) on an interval from 1 minute to 7 days. The LLM selects tools from the 51-tool registry — no manual chain selection.

**Step 4 — Execute** &nbsp; Every write operation is gated by spending cap enforcement and checked against the agent's current balance before broadcast. Real-time SSE confirmation streams tx status back to the chat. Scheduled runs log success/error and approximate Pocket relay usage per run.

**Step 5 — Monitor** &nbsp; The analytics dashboard tracks relay volume, chain health probes, latency comparisons, and cost breakdowns. Automations show last result, last run time, and relay counts for the last 10 runs.

---

## Value Proposition — What PocketAgent Brings to Pocket Network

[Pocket Network](https://www.pokt.network/) provides open, permissionless, multi-chain RPC through the Shannon gateway — the foundation this project builds on. PocketAgent is an application layer that sits on top of that foundation: AI agents that chat, act, and (with **Automations**) run on a schedule, with every chain read and write routed through Pocket.

| How PocketAgent extends the experience | In practice |
| :--- | :--- |
| **Continuous agent workloads** | Beyond interactive chat, **Automations** schedule the same LLM + tool path on intervals from 1 minute to 7 days — portfolio checks, gas comparisons, balance monitors, and more — so agents can keep using Pocket relays around the clock when users want that. |
| **Natural multi-chain tool use** | Fifty-one tools span six protocol families (EVM, Cosmos, Solana, SUI, NEAR, TRON). A single prompt can fan out across an agent’s selected chains, putting Pocket’s broad network coverage to work in one conversational or automated flow. |
| **A simple surface for multi-chain ops** | Users describe intent in natural language; the agent handles chain selection and tools. Unified multi-protocol wallets and the web UI make Pocket-backed multi-chain operations approachable for more people. |
| **An open AI + Shannon reference** | PocketAgent is a full-stack, open example of agents (chat, REST API, MCP, and scheduled jobs) using **Shannon as their RPC backbone**. It is meant to help others see and reuse that pattern. |
| **Clear relay visibility** | Dashboard analytics track relay volume and cost. Automations add per-run history and **relay counts for the last ten runs**, so users can see how their agents exercise Pocket in concrete, timestamped actions. |

PocketAgent does not compete with Pocket Network — it **celebrates and applies it**: Shannon supplies the relays; agents and Automations supply the workflows that generate and surface them.

---

## How does PocketAgent benefit everyday users — from complete beginners to developers?

PocketAgent meets people exactly where they are. You don't need to know what an RPC endpoint is to use it — you just type what you want in plain English, and the AI handles the blockchain complexity behind the scenes.

### 🐣 For the total novice (never touched crypto before)
No wallets to configure, no gas fee jargon to learn, no seed phrase panic. They can ask something like "what's my balance?" or "send $5 worth of ETH to my friend" in normal words, and PocketAgent translates that into the correct on-chain action. It removes the biggest barrier to crypto adoption: the intimidating learning curve.

### ⚡ For the amateur / casual crypto user
They know the basics but don't want to juggle five different wallet apps or manually check gas prices across chains. PocketAgent lets them compare fees across Ethereum, Polygon, and other chains in one sentence, then execute the cheapest option automatically. It saves time and prevents costly mistakes (like overpaying gas or sending to the wrong network).

### 🏆 For the serious crypto user
Power users get multi-chain visibility in one place — 52 chains, one interface, no juggling RPC providers or block explorers. The Automations feature lets them schedule recurring actions (like checking balances or executing strategies) without babysitting the app 24/7. The relay analytics dashboard also gives them real transparency into what's happening under the hood, which matters to people who actually care about decentralization.

### 🛠️ For developers
This is where the MCP server (pokt-agent-mcp) comes in. Developers can drop Pocket Network's 52-chain reach directly into tools they already use — Claude Desktop, Cursor — and query balances, simulate transactions, or analyze wallets without leaving their editor. No separate SDK to learn, no API key to request. It turns blockchain access into just another tool in their existing workflow.

### 💡 The common thread across all four groups
> Nobody has to sign up for Infura or Alchemy, manage API keys, or understand which RPC endpoint goes with which chain. PocketAgent — powered entirely by Pocket Network's permissionless infrastructure — hides that complexity so anyone, at any skill level, can interact with 52 blockchains just by describing what they want.

---

## Key Features

### AI Agent Layer

| Feature | Description |
| :--- | :--- |
| **Natural-language orchestration** | The LLM selects and chains 51 blockchain tools autonomously — no manual tool selection, no context switching between chains |
| **Agent lifecycle management** | Full CRUD via REST API and web UI: create, configure capabilities, set spending caps, update, soft-delete |
| **Per-agent access tokens** | JWT-based authentication with reissue, rotate, import, and export lifecycle. BroadcastChannel syncs tokens across browser tabs in real time |
| **Encrypted wallet storage** | AES-256 encryption per agent. Private keys never leave the backend in plaintext |
| **Automations** | Recurring scheduled prompts per agent — interval jobs (1m–7d), enable/disable, last result, and Pocket relay counts for the last 10 runs |

### Blockchain Operations

| Feature | Description |
| :--- | :--- |
| **52 chains, 6 protocol families** | EVM (36 chains), Cosmos (12), Solana, SUI, NEAR, TRON — all through a single unified toolset |
| **Decentralized RPC** | All traffic routes through Pocket Network's Shannon gateway (`https://{chain}.api.pocket.network`) — no Infura, no Alchemy, no centralized API keys |
| **Multi-protocol contract calls** | `contract_call` supports EVM, Solana, CosmWasm, SUI Move, NEAR, and TRON — read and write modes |
| **Non-EVM token transfers** | SPL tokens (Solana), TRC-20 (Tron), CW20 & IBC (Cosmos), NEP-141 (NEAR), SUI coins — each with dedicated tools |
| **Transaction simulation** | Dry-run transactions before broadcasting — covers all 6 protocol families |
| **Real-time confirmation streaming** | SSE-based pub/sub broker fans out transaction confirmations, reversions, and timeouts to the chat UI |

### Wallet & Portfolio

| Feature | Description |
| :--- | :--- |
| **Unified multi-chain portfolio** | Single `analyze_wallet` call returns balances, fiat valuations (via CoinGecko), and aggregated holdings |
| **Token discovery** | Automated token info queries for ERC-20, SPL, TRC-20, CW20, and NEP-141 tokens |
| **Chain comparison engine** | Compare gas fees, network latency, and chain suitability for transaction routing |
| **Spending cap enforcement** | Per-chain caps evaluated against wallet balance before any transaction broadcast |

### Platform & Developer Experience

| Feature | Description |
| :--- | :--- |
| **REST API** | Agents, chat, analytics, and automations — auto-generated Swagger UI at `/docs` and ReDoc at `/redoc` |
| **MCP server** | Standalone stdio server — 51 tools, 5 resources, 4 prompts. Drop into Claude Desktop, Cursor, or Codex |
| **Analytics dashboard** | Relay stats, chain health probes, cost tracking, and portfolio view with agent-scope filtering |
| **Automations UI** | Web page at `/scheduled-tasks` — templates, toggles, expand relay breakdown, copy-as-cURL |
| **Dark/light theme** | System preference detection with manual toggle |
| **WalletConnect** | RainbowKit + Wagmi for external wallet connections |

---

## Architecture

```
                                  ┌──────────────────────────────┐
                                  │  Claude Desktop · Cursor     │
                                  │       (MCP Clients)          │
                                  └──────────────┬───────────────┘
                                                 │ stdio
                                  ┌──────────────▼───────────────┐
                                  │     MCP Server (stdio)        │
                                  │  51 Tools · 5 Resources       │
                                  │  4 Prompts                    │
                                  └──────────────┬───────────────┘
                                                 │
 ┌──────────────────────┐      ┌─────────────────▼──────────────┐
 │  Next.js 16 · React  │◄────►│        FastAPI Backend          │
 │  19 Frontend         │ REST │                                │
 │                      │      │  /api/agents   (CRUD + tokens) │
 │  • Landing Page      │      │  /api/chat     (SSE stream)    │
 │  • Agent Management  │      │  /api/analytics                │
 │  • Chat Interface    │      │  /api/scheduled-tasks          │
 │  • Automations       │      │  /health                       │
 │  • Analytics         │      │                                │
 │  • Token UX          │      │  services/                     │
 │  • Wallet Connect    │      │    ai_agent.py      (LLM orch) │
 │                      │      │    pocket_rpc.py    (gateway)  │
 │  RainbowKit          │      │    scheduler.py     (jobs)     │
 │  Zustand · TanStack  │      │    chain_router.py  (dispatch) │
 │  shadcn/ui · Motion  │      │    chain_registry.py(52 chains)│
 └──────────────────────┘      │    wallets.py · encryption.py  │
                               │    confirmation.py  (SSE pub)  │
                               │    price_feed.py · relay_tracker│
                               │    */transfer.py    (6 protos) │
                               │                                │
                               │  tools/ (51 tools, 10 modules) │
                               │  database.py (SQLite/aiosqlite)│
                               └────────────────┬───────────────┘
                                                │ HTTP
                               ┌────────────────▼───────────────┐
                               │ Pocket Network Shannon Gateway │
                               │   Decentralized RPC (52 chains)│
                               │                                │
                               │  EVM ◇ Solana ◇ SUI ◇ NEAR    │
                               │  Cosmos ◇ TRON                 │
                               └────────────────────────────────┘
```

| Layer | Technology |
| :--- | :--- |
| **Frontend** | Next.js 16, React 19, TypeScript (strict), Tailwind CSS 4, shadcn/ui (new-york) |
| **State / Data** | Zustand v5, TanStack React Query v5 |
| **Web3** | RainbowKit v2, Wagmi v2, Viem v2 |
| **Animation** | Motion (Framer Motion) |
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **AI** | OpenAI-compatible API with function calling (tool-use) |
| **Database** | SQLite via aiosqlite (async) |
| **Auth / Crypto** | AES-256 wallet encryption (cryptography), JWT agent access tokens |
| **Blockchain SDKs** | web3, solders, tronpy, cosmpy, py-near, pysui |
| **MCP** | mcp ≥ 1.28.0 (Model Context Protocol) |
| **Testing** | pytest 9+ (175 back-end), Vitest 4 (77 front-end) |
| **Deployment** | Docker Compose, GitHub Actions CI |

---

## Quick Start

### Prerequisites

- **Node.js** v20+
- **Python** v3.11+
- **OpenAI-compatible API key** (any provider with a `/v1/chat/completions` endpoint)
- **WalletConnect Project ID** ([cloud.walletconnect.com](https://cloud.walletconnect.com/))

### One command

```bash
bash start.sh        # Unix
start.bat            # Windows
```

Both scripts start the backend, wait for it to become healthy, then launch the frontend. Logs go to `tmp/`.

### Root orchestrator

```bash
npm install
npm run dev          # runs both services via concurrently
```

### Docker

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with OPENAI_API_KEY, ENCRYPTION_KEY, JWT_SECRET
docker compose up --build
```

| Service | URL |
| :--- | :--- |
| Web UI | `http://localhost:3000` |
| API | `http://localhost:8000` |
| Swagger | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |

### Manual per-service

<details>
<summary>Backend</summary>

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
</details>

<details>
<summary>Frontend</summary>

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```
</details>

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `OPENAI_API_KEY` | Yes | — | LLM provider API key |
| `OPENAI_BASE_URL` | No | `https://api.openai.com/v1` | OpenAI-compatible base URL |
| `OPENAI_MODEL` | No | `gpt-4o` | Model identifier |
| `ENCRYPTION_KEY` | Yes | — | 32-byte AES key for agent wallet encryption |
| `JWT_SECRET` | Yes | — | Signing key for agent access tokens |
| `DATABASE_PATH` | No | `./data/pocketagent.db` | SQLite database location |
| `CORS_ORIGINS` | No | — | Allowed CORS origins (comma-separated) |
| `COINGECKO_API_KEY` | No | — | CoinGecko API key for fiat valuations |
| `NOTIONAL_POKT_PER_RELAY` | No | `0.00089` | Estimated POKT cost per relay |

### Frontend (`frontend/.env.local`)

| Variable | Required | Description |
| :--- | :---: | :--- |
| `NEXT_PUBLIC_API_URL` | Yes | Backend API base URL |
| `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID` | Yes | WalletConnect project ID |

---

## API Reference

Interactive docs at `/docs` (Swagger) and `/redoc` when the server is running.

### Agent Management

| Method | Route | Auth | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/agents` | — | Create agent (returns 201) |
| `GET` | `/api/agents` | — | List all agents |
| `GET` | `/api/agents/{id}` | Token | Get agent detail |
| `PUT` | `/api/agents/{id}` | Token | Update agent config |
| `DELETE` | `/api/agents/{id}` | Token | Soft-delete agent (204) |
| `POST` | `/api/agents/{id}/fund` | Token | Get funding instructions per chain |
| `GET` | `/api/agents/{id}/balances` | Token | Get balances across all chains |
| `GET` | `/api/agents/{id}/reissue-challenge` | Token | Get token reissue signing message |
| `POST` | `/api/agents/{id}/reissue-token` | Token | Reissue access token (invalidates old) |

### Chat & Analytics

| Method | Route | Auth | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/chat` | Token | Send message to agent (JSON or use `/api/chat/stream` for SSE) |
| `GET` | `/api/analytics/relay-stats` | — | Relay traffic statistics |
| `GET` | `/api/analytics/cost-breakdown` | — | Cost breakdown by chain/agent |

### Automations (scheduled tasks)

Recurring prompts run by a background scheduler (30s poll). Each run invokes the same LLM + tool path as chat. Relay counts attribute Pocket RPC usage per run when tools hit the chain.

| Method | Route | Auth | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/scheduled-tasks` | Token | Create automation (`agent_id`, `prompt`, `interval_seconds` 60–604800) |
| `GET` | `/api/scheduled-tasks?agent_id=` | Token | List automations for an agent (`agent_id` required) |
| `GET` | `/api/scheduled-tasks/{id}` | Token | Get one automation |
| `PATCH` | `/api/scheduled-tasks/{id}` | Token | Update prompt, interval, and/or `enabled` |
| `DELETE` | `/api/scheduled-tasks/{id}` | Token | Delete automation (204) |
| `GET` | `/api/scheduled-tasks/{id}/relay-stats` | Token | Last 10 runs + approximate relay totals |

Agent-scoped endpoints require the `X-Agent-Access-Token` header.

**UI:** open **Automations** in the app nav (`/scheduled-tasks`) — templates, enable toggle, last result, relay breakdown, and copy-as-cURL.

---

## Supported Chains

**52 production networks** across 6 protocol families:

| Protocol | Count | Chains |
| :--- | ---: | :--- |
| **EVM** | 36 | Ethereum, Polygon, Arbitrum, Optimism, Base, BNB, Avalanche, Fantom, Gnosis, Berachain, Blast, Celo, Linea, Scroll, zkSync Era, Sonic, Polygon zkEVM, Fraxtal, opBNB, Kaia, Kava, Moonbeam, Moonriver, Metis, Boba, Fuse, Harmony, IoTeX, Oasys, Sei EVM, Hyperliquid, Ink, Taiko, Unichain, XRPL EVM, zkLink Nova |
| **Cosmos** | 12 | Osmosis, Pocket, Akash, Juno, Seda, Persistence, Fetch.ai, Jackal, Cheqd, Chihuahua, Shentu, AtomOne |
| **Solana** | 1 | Solana Mainnet-Beta |
| **SUI** | 1 | SUI Mainnet |
| **NEAR** | 1 | NEAR Protocol Mainnet |
| **TRON** | 1 | TRON Mainnet |

*Registry: [`backend/services/chain_registry.py`](backend/services/chain_registry.py)*

---

## Tools

The LLM has access to **51 tools** across 10 modules. Each tool is a typed function the agent can call autonomously.

The 32 read tools build on the foundation laid by **BlockchainQuery**, the official PNF MCP server, reimplemented against Pocket Network RPC. PocketAgent extends this base with **19 additional custom tools** — chain comparison, guarded multi-protocol writes, non-EVM token transfers, transaction simulation, portfolio analysis, POKT cost estimation, and analytics.

| Module | Tools | What it does |
| :--- | ---: | :--- |
| `balance_tools` | 6 | Native balance queries across EVM, Solana, Cosmos, SUI + cross-chain comparison + unit conversion |
| `chain_tools` | 2 | List all chains, get per-chain metadata (RPC URL, explorer, decimals) |
| `compare_tools` | 3 | Compare gas fees, recommend optimal chains, estimate transaction costs |
| `transaction_tools` | 15 | 12 read tools (blocks, txns, receipts, signatures) + 3 write tools: `send_transaction`, `send_erc20`, `contract_call` |
| `token_tools` | 13 | Token info, contract calls, event logs, domain resolution across all protocols |
| `token_transfer_tools` | 6 | Non-EVM transfers: `send_spl_token`, `send_trc20_token`, `send_ibc_token`, `send_cw20_token`, `send_sui_token`, `send_nep141_token` |
| `simulation_tools` | 1 | Dry-run transactions before broadcast |
| `wallet_tools` | 1 | Multi-chain portfolio report with CoinGecko valuations |
| `pokt_tools` | 1 | Estimate relay cost in POKT |
| `analytics_tools` | 3 | Relay stats, relay history, cost breakdown |

### Safety guarantees

- **Read tools** are always available — no chain cost beyond relay fees.
- **Write tools** are gated behind per-agent spending caps, enforced before broadcast.
- **Simulation** runs dry and returns expected effects without spending.
- **Testnet rejection** — write tools reject testnet/Tenderly URLs in production.

---

## MCP Integration

PocketAgent ships as a **pip-installable MCP server**. Developers can add PocketAgent's 51 blockchain tools directly to their AI editor or agent in two steps.

### Install

```bash
pip install pokt-agent-mcp
```

Or from source:

```bash
git clone https://github.com/Jayanng/PocketAgent.git
pip install ./PocketAgent/backend
```

### Configure your MCP client

Add this to your `claude_desktop_config.json`, `.cursor/mcp.json`, or equivalent:

```json
{
  "mcpServers": {
    "pocketagent": {
      "command": "python",
      "args": ["-m", "pocketagent.mcp_server.server"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "ENCRYPTION_KEY": "...",
        "JWT_SECRET": "..."
      }
    }
  }
}
```

Or use the convenience entry point after pip install:

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

### Resources

| URI | Description |
| :--- | :--- |
| `pocket://chains` | All supported chains with metadata |
| `pocket://chains/{chain}/status` | Real-time chain health |
| `pocket://agents/{id}/stats` | Agent relay statistics |
| `pocket://agents/{id}/wallet` | Agent wallet context |
| `pocket://cache/stats` | Cache hit/miss metrics |

### Prompts

| Prompt | Description |
| :--- | :--- |
| `analyze_wallet` | Analyze a wallet across all chains |
| `find_cheapest_chain` | Find the cheapest chain for an operation |
| `track_pokt_costs` | Track POKT relay costs over time |
| `compare_and_recommend` | Compare chains and recommend the best |

Full docs: [`docs/mcp-server.md`](docs/mcp-server.md)

---

## Reliability

- **Graceful failure isolation** — RPC timeouts or degraded nodes return `{ "available": false }` instead of crashing the agent loop.
- **Structured error handling** — Non-JSON gateway responses (empty bodies, HTML error pages) are detected and converted to structured `RuntimeError` messages.
- **Intelligent retries** — Exponential backoff for rate limits (429), gateway timeouts (408), and server errors (5xx).
- **Spending cap enforcement** — Per-chain caps evaluated against wallet balance before every broadcast.
- **Mainnet-only write guards** — Write operations reject testnet and Tenderly URLs in production.
- **Chain health probes** — Dashboard periodically checks all 52 endpoints and surfaces availability.

---

## Testing

**252 automated tests** (175 backend + 77 frontend). CI runs on every push and PR via GitHub Actions.

| Suite | Framework | Run |
| :--- | :--- | :--- |
| Backend | pytest 9 + aiosqlite + FastAPI TestClient | `cd backend && .venv\Scripts\pytest.exe -q` |
| Frontend | Vitest 4 + React Testing Library + jsdom | `cd frontend && node node_modules/vitest/dist/cli.js run` |

**Coverage highlights:** wallet signature verification (18 tests across all 6 chains), token reissue lifecycle (10 tests), token UX components (25 tests), agent store actions (8 tests), API client methods (11 tests), chain badge symbols (3 tests), chat chain inference (3 tests), chain registry parity, database migration, dashboard endpoints, MCP server (hermetic + live), and live RPC integration.

Manual QA plans: [`docs/superpowers/plans/2026-06-30-token-ux-qa.md`](docs/superpowers/plans/2026-06-30-token-ux-qa.md)

---

## Known Limitations

- **Radix** is not supported — Pocket Network has no public Radix RPC endpoint.
- **ERC-20 transfers** are EVM-only. Non-EVM protocols use dedicated tools: `send_spl_token`, `send_trc20_token`, `send_ibc_token` / `send_cw20_token`, `send_sui_token`, `send_nep141_token`.
- **SUI writes** bootstrap from a one-time Mysten fullnode call (`suix_getCoins`) when an agent has zero tracked coins. Subsequent operations use Pocket RPC exclusively.

---

## License

MIT — see [LICENSE](LICENSE).
