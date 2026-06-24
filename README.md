# PocketAgent

**AI agents for the multi-chain world — powered by [Pocket Network](https://www.pokt.network/).**

PocketAgent is a full-stack platform for creating, managing, and conversing with AI
agents that read and compare **52 blockchains** through Pocket Network's decentralized
RPC infrastructure. Agents reason about balances, gas, and chain health across EVM,
Solana, Sui, Near, Tron, and Cosmos — with guarded native transaction signing on EVM,
Solana, and Tron. Drive them through the web UI, the REST API, or any MCP-compatible
client, all using the same 49 on-chain tools.

[![CI](https://github.com/Jayanng/PocketAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/Jayanng/PocketAgent/actions/workflows/ci.yml)
![Python 3.11](https://img.shields.io/badge/python-3.11-blue)
![Chains](https://img.shields.io/badge/chains-52-purple)

---

## Why PocketAgent

- **One interface, six protocols.** EVM, Solana, Sui, Near, Tron, and Cosmos behind a
  single agent — no per-chain SDKs to wire up.
- **No centralized RPC keys.** Every request routes through Pocket Network's public
  Shannon gateway (`{chain}.api.pocket.network`); there is nothing to sign up for or pay.
- **49 tools, function-calling ready.** Balances, gas comparison, chain routing, wallet
  analysis, simulation, and guarded writes — exposed to the LLM as OpenAI-style tools and
  to MCP clients as MCP tools.
- **Agent wallets with guardrails.** Per-agent encrypted EVM, Solana, and Tron keys with
  per-chain spending caps enforced *before* broadcast.
- **Built to stay up.** A degraded upstream chain returns a structured "unavailable"
  result instead of crashing the agent turn — one bad chain never breaks the rest.
- **Observable by default.** Relay stats, chain health, and cost tracking surface in the
  dashboard and via analytics endpoints.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (Next.js 16 · React 19)                        │
│  Chat · Dashboard · Agent management · Wallet (Wagmi)   │
├─────────────────────────────────────────────────────────┤
│  Backend (FastAPI · SQLite)                              │
│  AI agent service · PocketRPC · Chain router · MCP       │
├─────────────────────────────────────────────────────────┤
│  Pocket Network (decentralized RPC, Shannon gateway)     │
└─────────────────────────────────────────────────────────┘
```

| Layer    | Stack                                                                   |
| -------- | ----------------------------------------------------------------------- |
| Frontend | Next.js 16, React 19, Tailwind CSS 4, RainbowKit, Wagmi, Zustand       |
| Backend  | FastAPI, SQLite (aiosqlite), OpenAI function calling, MCP              |
| RPC      | Pocket Network Shannon endpoints across 52 chains / 6 protocol families |

---

## Quick start

### Docker (recommended)

```bash
cp backend/.env.example backend/.env
# Edit backend/.env: set OPENAI_API_KEY, ENCRYPTION_KEY, JWT_SECRET

# Set frontend build-time values in the root .env (or your shell):
#   NEXT_PUBLIC_API_URL=http://localhost:8000
#   NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=<your-walletconnect-project-id>

docker compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
```

### Manual setup

#### Prerequisites

- **Node.js** 20+
- **Python** 3.11+
- An **OpenAI-compatible API key** (OpenAI or [GMI Serving](https://gmi-serving.com/))
- A [WalletConnect](https://cloud.walletconnect.com/) project ID

#### 1. Clone

```bash
git clone https://github.com/Jayanng/PocketAgent.git
cd PocketAgent
```

#### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env — set OPENAI_API_KEY (or GMI_API_KEY), ENCRYPTION_KEY, and JWT_SECRET
```

Start the API:

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive API docs: <http://127.0.0.1:8000/docs>

#### 3. Frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local — set NEXT_PUBLIC_API_URL and a real NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID
npm run dev
```

Open <http://localhost:3000>.

---

## Environment variables

### Backend (`backend/.env`)

| Variable             | Description                                                                                  |
| -------------------- | -------------------------------------------------------------------------------------------- |
| `OPENAI_API_KEY`     | API key for the LLM provider (OpenAI)                                                        |
| `GMI_API_KEY`        | API key for GMI Serving (used when `OPENAI_BASE_URL` points at `gmi-serving.com`)            |
| `OPENAI_BASE_URL`    | OpenAI-compatible base URL (default: `https://api.openai.com/v1`)                            |
| `OPENAI_MODEL`       | Model name (e.g. `gpt-4o`, `openai/gpt-5.4-mini`)                                            |
| `ENCRYPTION_KEY`     | 32-byte key for agent wallet encryption (required)                                           |
| `JWT_SECRET`         | Secret for token signing (required)                                                           |
| `DATABASE_PATH`      | SQLite database path (default: `./data/pocketagent.db`; relative paths resolve from `backend/`) |
| `CORS_ORIGINS`       | Comma-separated browser origins allowed to call the API (default: local Next.js dev origins)  |
| `COINGECKO_API_KEY`  | Optional CoinGecko key for USD price enrichment                                              |
| `NOTIONAL_POKT_PER_RELAY` | Notional POKT cost per relay for cost estimates (default: `0.00089`)                    |

> Per-chain RPC URLs are defined in `backend/services/chain_registry.py` and are not
> currently overridable via environment variables. The `POCKET_RPC_*` keys in
> `.env.example` are retained for backward reference only.

### Frontend (`frontend/.env.local`)

| Variable                          | Description                                                               |
| --------------------------------- | ------------------------------------------------------------------------- |
| `NEXT_PUBLIC_API_URL`             | Backend URL (default: `http://localhost:8000`)                            |
| `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID` | Required WalletConnect Cloud project ID. Placeholder values are rejected at startup. |

For Docker, set the frontend variables in the root `.env` (or your shell) before
`docker compose up --build`; Next.js embeds `NEXT_PUBLIC_*` values into the browser
bundle during the image build.

---

## Supported chains

PocketAgent reads **52 mainnet chains** across six protocol families through the Pocket
Network Shannon gateway. Each chain is reachable at `https://{slug}.api.pocket.network`.

| Protocol | Examples                                                       |
| -------- | -------------------------------------------------------------- |
| EVM      | Ethereum, Polygon, Arbitrum, Optimism, Base, BNB, Blast, Sonic |
| Cosmos   | Osmosis, Akash, Juno, Persistence, AtomOne, Seda, Fetch        |
| Solana   | Solana                                                         |
| Sui      | Sui                                                            |
| Near     | Near                                                           |
| Tron     | Tron (EVM-compatible JSON-RPC + native REST)                   |

The full, authoritative list lives in `backend/services/chain_registry.py`
(and is mirrored in `frontend/src/lib/constants.ts`).

---

## Tool categories

| Category     | Examples                                                                                   |
| ------------ | ------------------------------------------------------------------------------------------ |
| **Read**     | `evm_get_balance`, `solana_get_balance`, `cosmos_get_balance`, `evm_get_block`, `list_chains` |
| **Compare**  | `compare_chains`, `recommend_chain`, `estimate_transaction_cost`                          |
| **Transact** | `send_transaction`, `send_erc20`, `contract_call` (EVM/Solana/Tron; other protocols defer) |
| **Analytics**| `analyze_wallet`, `get_relay_stats`, `get_cost_breakdown`                                 |
| **POKT**     | Pocket Network relay and notional cost tools                                               |

---

## MCP server

PocketAgent ships an MCP (Model Context Protocol) server that exposes all 49 tools, 5
resources, and 4 prompts over stdio. From the `backend` directory:

```bash
python -m mcp_server.server
```

Compatible with Claude Desktop, Cursor, Codex, and any other MCP client.
See `backend/mcp_server/` and `docs/mcp-server.md` for details.

---

## Project structure

```
PocketAgent/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Pydantic settings + env loading
│   ├── routers/             # REST API routes (agents, chat, analytics)
│   ├── services/            # PocketRPC, AI agent, chain router, price feed, wallets
│   ├── tools/               # 49 on-chain tool implementations
│   ├── mcp_server/          # Model Context Protocol adapter
│   └── tests/               # Pytest suite (hermetic + live)
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

### Tests

```bash
# Hermetic backend suite (run from the repository root — no extra env needed)
python -m pytest backend/tests/ -v

# Optional: live Pocket RPC checks (hits real endpoints)
LIVE_RPC_TESTS=1 python -m pytest backend/tests/test_live_rpc.py -v

# Frontend lint + build
cd frontend && npm run lint && npm run build
```

### Health check

```bash
curl http://127.0.0.1:8000/health
```

---

## Reliability

- Read and compare tools **degrade gracefully**: when an upstream Pocket RPC endpoint is
  unavailable (e.g. a chain returns 5xx or times out), the tool returns a structured
  `{"available": false, ...}` result instead of raising — so one degraded chain never
  aborts the whole agent turn.
- Multi-chain tools (`compare_balances`, `compare_chains`, `recommend_chain`) already
  isolate failures per chain; a single unhealthy chain is reported as degraded rather
  than failing the comparison.
- Transient gateway timeouts (HTTP 408) are retried alongside 429/5xx.

---

## Security notes

- Never commit `.env` or `.env.local` — both are gitignored.
- Generate strong values for `ENCRYPTION_KEY` and `JWT_SECRET` before running in production.
- Native EVM, Solana, and Tron transfer tools enforce per-agent, per-chain spending caps
  *before* broadcast.
- Cosmos, Sui, Near native transfers and non-EVM contract writes return a deferred status
  until protocol-specific signing is implemented.
- Use `simulate_transaction` and review transaction prompts before approving agent-initiated sends.

---

## License

This repository does not currently include a license file. Add one (e.g. MIT or Apache-2.0)
before open-sourcing — until then, default copyright applies and the code is not licensed
for redistribution or commercial use.

---

## Links

- **Repository:** [github.com/Jayanng/PocketAgent](https://github.com/Jayanng/PocketAgent)
- **Pocket Network:** [pokt.network](https://www.pokt.network/)
- **Pocket RPC docs:** [docs.pokt.network](https://docs.pokt.network/)
