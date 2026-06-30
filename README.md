# PocketAgent

**Enterprise-grade AI agent platform for the multi-chain ecosystem — powered by [Pocket Network](https://www.pokt.network/).**

PocketAgent is a production-ready, full-stack platform designed to create, coordinate, and orchestrate AI agents across **52 distinct blockchains** using Pocket Network's decentralized, trustless RPC infrastructure. 

Agents can reason about multi-chain states, query balances, analyze gas fees, and evaluate network latency across EVM, Solana, Sui, Near, Tron, and Cosmos protocols, with built-in transaction signing guards on EVM, Solana, Tron, Cosmos, Sui, and NEAR. Interact with your agents via a polished web dashboard, a developer-friendly REST API, or any client compatible with the Model Context Protocol (MCP).

---

## Key Features

* **Unified Protocol Interface**: Access EVM, Solana, Sui, Near, Tron, and Cosmos families under a single, standardized agent toolset.
* **Decentralized RPC Gateway**: Zero centralized API keys required. All requests route dynamically through the public Pocket Network Shannon gateway (`https://{chain}.api.pocket.network`).
* **MCP Compatibility**: Native support for the Model Context Protocol (MCP). Integrate agent workflows directly into developer environments such as Claude Desktop, Cursor, or Codex.
* **Guarded Transaction Signing**: Per-agent encrypted keys (EVM, Solana, Tron, Cosmos, Sui, NEAR) with configurable, protocol-enforced spending caps checked prior to broadcast.
* **Fault-Tolerant Execution**: Resilient fallback routines handle degraded upstream RPC nodes gracefully, returning structured status payloads instead of failing agent turns.
* **Operational Observability**: Real-time stats, relay volume, latency comparison, and cost tracking out-of-the-box.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Next.js 16 · React 19 Frontend             │
│    Sleek Chat · Dashboard · Agent Profiles · Wallet     │
├─────────────────────────────────────────────────────────┤
│                FastAPI · SQLite Backend                 │
│      AI Orchestrator · PocketRPC · MCP Server Core      │
├─────────────────────────────────────────────────────────┤
│            Pocket Network Shannon Gateway               │
│        Decentralized RPC Infrastructure (52 Chains)     │
└─────────────────────────────────────────────────────────┘
```

| Layer | Technology Stack |
| :--- | :--- |
| **Frontend** | Next.js 16, React 19, Tailwind CSS 4, RainbowKit, Wagmi, Zustand |
| **Backend** | FastAPI, SQLite (aiosqlite), OpenAI Function Calling, MCP |
| **RPC Gateway** | Pocket Network Shannon endpoints spanning 52 chains & 6 major protocol families |

---

## Quick Start

### 1. Docker Deployment (Recommended)

To run the complete suite containing the frontend, backend, and database:

```bash
# 1. Initialize environment variables
cp backend/.env.example backend/.env

# 2. Configure backend/.env with OPENAI_API_KEY, ENCRYPTION_KEY, and JWT_SECRET

# 3. Configure frontend variables in root .env or shell environment:
#    NEXT_PUBLIC_API_URL=http://localhost:8000
#    NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=<your-walletconnect-project-id>

# 4. Spin up the containers
docker compose up --build
```
* The Web UI will be active at `http://localhost:3000`
* The API Server will be active at `http://localhost:8000`

---

### 2. Manual Installation

#### Prerequisites
* Node.js v20+
* Python v3.11+
* OpenAI-compatible API credentials (or GMI Serving key)
* WalletConnect Project ID (obtainable via [WalletConnect Cloud](https://cloud.walletconnect.com/))

#### Backend Setup

```bash
cd backend
python -m venv .venv

# Activate Virtual Environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies and setup environment
pip install -r requirements.txt
cp .env.example .env

# Edit .env to set OPENAI_API_KEY, ENCRYPTION_KEY, and JWT_SECRET
```

Start the API development server:
```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be available at: `http://127.0.0.1:8000/docs`

#### Frontend Setup

In a separate terminal window:
```bash
cd frontend
npm install
cp .env.example .env.local

# Edit .env.local and configure NEXT_PUBLIC_API_URL and NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID
npm run dev
```
Access the application at `http://localhost:3000`.

---

## Environment Variables Configuration

### Backend Config (`backend/.env`)

| Variable | Required | Description |
| :--- | :---: | :--- |
| `OPENAI_API_KEY` | Yes | API credential for the language model provider |
| `OPENAI_BASE_URL` | No | Target OpenAI-compatible API base (default: `https://api.openai.com/v1`) |
| `OPENAI_MODEL` | No | Target model name (e.g. `gpt-4o`) |
| `ENCRYPTION_KEY` | Yes | 32-byte key used to securely encrypt agent wallets (falls back to `JWT_SECRET` if unset — set both independently in production) |
| `JWT_SECRET` | Yes | Signing key for authentication tokens |
| `DATABASE_PATH` | No | SQLite database file location (default: `./data/pocketagent.db`) |
| `CORS_ORIGINS` | No | Allowed CORS domains (comma-separated) |
| `COINGECKO_API_KEY` | No | Optional CoinGecko API key for asset valuation |
| `NOTIONAL_POKT_PER_RELAY` | No | Estimated POKT cost configuration per RPC relay (default: `0.00089`) |

### Frontend Config (`frontend/.env.local`)

| Variable | Required | Description |
| :--- | :---: | :--- |
| `NEXT_PUBLIC_API_URL` | Yes | Base URL pointing to the backend API server |
| `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID` | Yes | Required WalletConnect project identifier |

---

## Supported Ecosystems

PocketAgent interfaces with **52 production networks** across six major protocol architectures:

| Protocol | Scope | Supported Networks (Examples) |
| :--- | :---: | :--- |
| **EVM** | 40+ chains | Ethereum, Polygon, Arbitrum, Optimism, Base, BNB, Sonic, Blast, Scroll |
| **Solana** | L1 | Solana Mainnet-Beta |
| **Sui** | L1 | Sui Mainnet |
| **Near** | L1 | Near Protocol Mainnet |
| **Cosmos** | App-Chains | Osmosis, Akash, Juno, Persistence, AtomOne, Seda, Fetch.ai |
| **Tron** | L1 | Tron Mainnet (JSON-RPC & REST APIs) |

*Authoritative registry is defined in `backend/services/chain_registry.py`.*

---

## Tool Categories

PocketAgent features **44 predefined tools** exposed to the LLM agent and MCP interface:

1. **Read-only State**: `evm_get_balance`, `solana_get_balance`, `cosmos_get_balance`, `evm_get_block`, `list_chains`.
2. **Comparison Engines**: Gas fee comparison, network latency check, chain recommendation models.
3. **Transaction Execution**: `send_transaction`, `send_erc20`, `contract_call` (native writes on EVM, Solana, Tron, Cosmos, Sui, and NEAR; ERC-20 and contract writes are EVM-only).
4. **Analytics & Metrics**: Wallet analysis, Pocket Network stats, relay performance metrics.

---

## Model Context Protocol (MCP) Integration

The backend serves as a standalone MCP server, enabling LLMs in external clients (such as Claude Desktop, Cursor, or Codex) to execute the 44 blockchain tools natively.

From the `backend` folder:
```bash
python -m mcp_server.server
```
Detailed usage documentation can be found in `docs/mcp-server.md`.

---

## Diagnostics & Reliability

* **Graceful Failure Isolation**: Upstream RPC latency or network timeouts return standard `{"available": false}` objects instead of throwing exceptions. A single degraded node will not disrupt the remaining agent workspace loop.
* **Intelligent Retries**: Transparent client retries for gateway rate limits (429) and network gateway timeouts (408).
* **Guarded Writes**: Spending caps are evaluated per chain prior to broadcasting transactions, blocking excessive token outflows.

---

## Testing

PocketAgent ships with **182 automated tests** across two suites:

| Suite | Tests | Tooling | Command |
| :--- | ---: | :--- | :--- |
| **Backend** | 138 | pytest 9 · aiosqlite · FastAPI TestClient | `cd backend && .venv\Scripts\pytest.exe -q` |
| **Frontend** | 44  | Vitest 4 · React Testing Library · jsdom | `cd frontend && node.exe node_modules/vitest/dist/cli.js run` |
| **Total**  | **182** | | |

### Test coverage highlights

* **Database migration** — additive `access_token_created_at` / `access_token_revoked_at` columns, idempotent init.
* **Environment convention** — 3 tests enforcing that root `.env` only contains `NEXT_PUBLIC_*` keys and provides `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID`.
* **Per-chain wallet signature verification** — 18 unit tests covering all 6 supported chains (EVM, Solana, Sui, NEAR, Cosmos, TRON) with valid-signature, invalid-signature, and wrong-address vectors per chain.
* **Token reissue endpoints** — 9 endpoint tests + 1 full lifecycle test covering `current_token` and `wallet_signature` proofs, expired-challenge rejection (422), and wrong-signer rejection (401).
* **TokenStore** — 8 unit tests covering localStorage persistence, in-memory cache, BroadcastChannel cross-tab sync, listener notifications, and quota-exceeded fallback.
* **API client reissue methods** — 11 unit tests covering `api.agents.reissue`, `api.agents.reissueChallenge`, and the `get/remember/forget` token helpers' delegation to TokenStore.
* **Agent store actions** — 8 unit tests covering `rotateAgentAccessToken` (success, no-token error, server error, isRotating state), `exportAllAgentTokens` (download trigger), and `importAgentAccessToken` (success, validation, error capture).
* **Token UI components** — 17 component tests across `TokenDisplayModal`, `TokenPanel`, `TokenImportDialog`, and `TokenRotateDialog`.

### Running the suites

```bash
# Backend (from repo root)
cd backend
set PYTHONPATH=..  # Windows; Linux/macOS: PYTHONPATH=..
.venv\Scripts\pytest.exe -q

# Frontend (from repo root)
cd frontend
node.exe node_modules/vitest/dist/cli.js run
```

Manual end-to-end flows (multi-tab sync, wallet-sign recovery, race conditions) are documented in `docs/superpowers/plans/2026-06-30-token-ux-qa.md`.

---

## AI Usage Disclosure

This project was built with assistance from AI coding tools, including **Cursor** (Claude-based agent), **Grok**, and **OpenAI** models for implementation, testing, and documentation. Human developers reviewed and integrated all generated code.

---

## Known Limitations

- **Radix** is not supported. Pocket Network does not expose a public Radix RPC endpoint, so Radix read/write tools were removed from the MCP tool registry.
- **ERC-20 and contract writes** are EVM-only. Other protocol families support native transfers via `send_transaction`.
- **Sui writes** (`send_transaction`) use Pocket Network RPC exclusively after initial wallet funding: gas estimation (`sui_dryRunTransactionBlock`), object refresh (`sui_getObject`), signing, and broadcast (`sui_executeTransactionBlock`) all go through `sui.api.pocket.network`. Coin objects are tracked locally per agent (`sui_tracked_coins`); Pocket's indexed list methods (`suix_getCoins`, `suix_getOwnedObjects`, and legacy `sui_getOwnedObjects`) are unavailable (`Index store not available` / `Method not found`). A **one-time Mysten fullnode bootstrap** (`suix_getCoins` only, when an agent has zero tracked coins) seeds the local index; subsequent sends refresh known coin IDs via Pocket `sui_getObject` and update the index from transaction effects.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
