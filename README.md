# PocketAgent

**AI agents for the multi-chain world — powered by [Pocket Network](https://www.pokt.network/).**

PocketAgent is a full-stack platform for creating, managing, and conversing with AI agents that read, compare, and transact across **60+ blockchains** through Pocket Network's decentralized RPC infrastructure. Use the web UI or connect any MCP-compatible client to drive the same 49 on-chain tools.

[![CI](https://github.com/Jayanng/PocketAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/Jayanng/PocketAgent/actions/workflows/ci.yml)

---

## Features

- **Multi-protocol by default** — EVM, Solana, Sui, Near, Tron, and Cosmos through one agent interface
- **49 registered tools** — balances, gas comparison, chain routing, wallet analysis, and guarded write operations
- **Agent wallets** — per-agent encrypted keys with spending caps and autonomous transaction signing
- **MCP server** — expose all tools, resources, and prompts to Claude Desktop, Cursor, Codex, and other MCP clients
- **Dashboard** — relay stats, chain health, cost tracking, and multi-chain portfolio views
- **No centralized RPC keys** — routes through Pocket Network public endpoints (`{chain}.api.pocket.network`)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (Next.js 16 + React 19)                       │
│  Chat · Dashboard · Agent management · Wallet (Wagmi)   │
├─────────────────────────────────────────────────────────┤
│  Backend (FastAPI + SQLite)                             │
│  AI agent service · PocketRPC · Chain router · MCP      │
├─────────────────────────────────────────────────────────┤
│  Pocket Network (decentralized RPC)                     │
└─────────────────────────────────────────────────────────┘
```

| Layer | Stack |
|-------|-------|
| Frontend | Next.js 16, React 19, Tailwind CSS 4, RainbowKit, Wagmi, Zustand |
| Backend | FastAPI, SQLite, OpenAI function calling, MCP |
| RPC | Pocket Network Shannon endpoints across 50+ chains |

---

## Quick start

### Prerequisites

- **Node.js** 20+
- **Python** 3.11+
- An **OpenAI-compatible API key** (OpenAI or GMI Serving)
- Optional: [WalletConnect](https://cloud.walletconnect.com/) project ID for wallet connection

### 1. Clone the repository

```bash
git clone https://github.com/Jayanng/PocketAgent.git
cd PocketAgent
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env — set OPENAI_API_KEY, ENCRYPTION_KEY, and JWT_SECRET at minimum
```

Start the API:

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 3. Frontend setup

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local — set NEXT_PUBLIC_API_URL and NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Environment variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | API key for the LLM provider |
| `OPENAI_BASE_URL` | OpenAI-compatible base URL (default: `https://api.openai.com/v1`) |
| `OPENAI_MODEL` | Model name (e.g. `gpt-4o`) |
| `ENCRYPTION_KEY` | 32-byte key for agent wallet encryption |
| `JWT_SECRET` | Secret for token signing |
| `DATABASE_PATH` | SQLite database path (default: `./pocketagent.db`) |
| `POCKET_RPC_*` | Per-chain Pocket Network RPC URLs (see `.env.example`) |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend URL (default: `http://localhost:8000`) |
| `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID` | WalletConnect Cloud project ID |

---

## MCP server

PocketAgent ships an MCP server that exposes all 49 tools over stdio. From the `backend` directory:

```bash
python -m mcp_server.server
```

Compatible with any MCP client. See `backend/mcp_server/` for tools, resources, and prompts.

---

## Project structure

```
PocketAgent/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── routers/             # REST API routes
│   ├── services/            # RPC client, AI agent, chain router, price feed
│   ├── tools/               # 49 on-chain tool implementations
│   ├── mcp_server/          # Model Context Protocol adapter
│   └── tests/               # Pytest suite
├── frontend/
│   └── src/
│       ├── app/             # Next.js App Router pages
│       ├── components/      # UI, agents, chat, dashboard, wallet
│       └── lib/             # API client, stores, constants
├── docs/                    # Specifications and design docs
└── .github/workflows/       # CI (backend tests, MCP smoke, frontend build)
```

---

## Development

### Run tests

```bash
# Backend
cd backend && python -m pytest tests/ -v

# Frontend lint + build
cd frontend && npm run lint && npm run build
```

### API health check

```bash
curl http://127.0.0.1:8000/health
```

---

## Tool categories

| Category | Examples |
|----------|----------|
| **Read** | `evm_get_balance`, `solana_get_balance`, `list_chains`, `evm_get_block` |
| **Compare** | `compare_gas`, `compare_chains`, `find_cheapest_chain`, `recommend_chain` |
| **Transact** | `send_transaction`, `send_erc20`, `contract_call` |
| **Analytics** | `analyze_wallet`, `get_relay_stats`, `get_cost_breakdown` |
| **POKT** | Pocket Network–specific relay and cost tools |

---

## Security notes

- Never commit `.env` or `.env.local` — they are gitignored.
- Generate strong values for `ENCRYPTION_KEY` and `JWT_SECRET` before running in production.
- Agent write tools enforce spending caps and simulation before broadcast.
- Review transaction prompts carefully before approving agent-initiated sends.

---

## License

This project is provided as-is. Add a license file if you intend to open-source under a specific terms.

---

## Links

- **Repository:** [github.com/Jayanng/PocketAgent](https://github.com/Jayanng/PocketAgent)
- **Pocket Network:** [pokt.network](https://www.pokt.network/)
- **Pocket RPC docs:** [docs.pokt.network](https://docs.pokt.network/)
