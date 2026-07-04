# POCKETAGENT — Non-EVM Write Tools Implementation Prompt

## PROJECT CONTEXT

PocketAgent is an enterprise-grade AI agent platform for the multi-chain ecosystem, powered by Pocket Network decentralized RPC. It's a monorepo at `C:\Users\dell\Documents\VS_code\PocketAgent` with:

- **Frontend**: Next.js 16 (React 19, wagmi, rainbowkit, zustand) at `frontend/` — runs on `http://localhost:3000`
- **Backend**: Python FastAPI (uvicorn) at `backend/` — runs on `http://localhost:8000`
- **LLM provider**: NVIDIA NIM (`https://integrate.api.nvidia.com/v1`), model `meta/llama-3.1-8b-instruct` (configured in `backend/.env`)
- **Start servers**: `npm run dev` from root (uses `concurrently`), or individually: `npm run dev:frontend` / `npm run dev:backend`
- **Backend venv**: `backend/.venv` (Windows: `backend/.venv/Scripts/python.exe`)
- **Backend launcher**: `scripts/dev-backend.js` — it STRIPS stale OS env vars (OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, GMI_API_KEY) so `backend/.env` is the single source of truth for provider config.

## CURRENT STATE (already completed in prior sessions)

1. **LLM switched** from slow 70B to fast `meta/llama-3.1-8b-instruct` (NVIDIA NIM). Config in `backend/.env`.
2. **Generation tuning added**: `OPENAI_TEMPERATURE=0.3`, `OPENAI_MAX_TOKENS=1024`, `CHAT_HISTORY_LIMIT=20` (in `backend/config.py` + `backend/.env`).
3. **Anti-hallucination system prompt** added to `backend/services/ai_agent.py` `get_system_prompt()` — forces the model to ALWAYS call tools for live blockchain data, never fabricate.
4. **Tool arg normalization** (`_normalize_args` in `ai_agent.py`) — converts Python-repr strings (e.g. `"['ethereum', 'polygon']"`) that smaller models emit into real JSON lists using `ast.literal_eval`.
5. **All 34 read/compare/analytics tools verified** working with live Pocket RPC data (34/34 passed).
6. **Write tools audited**: `send_transaction` covers all 52 chains (6 protocols: evm, solana, tron, sui, cosmos, near) — all signing libraries installed. BUT `send_erc20` and `contract_call` are **EVM-only** — they return a "deferred" stub for non-EVM chains.


## THE CHAIN REGISTRY (52 chains total)

File: `backend/services/chain_registry.py`

| Protocol | Count | Chains |
|---|---|---|
| evm | 36 | ethereum, polygon, arbitrum, optimism, bsc, avalanche, fantom, gnosis, base, berachain, blast, celo, linea, scroll, zksync-era, sonic, polygon-zkevm, fraxtal, fuse, harmony, hyperliquid, ink, iotex, kaia, kava, metis, moonbeam, moonriver, oasys, opbnb, sei, taiko, unichain, xrplevm, zklink-nova, boba |
| cosmos | 12 | osmosis, pocket, akash, juno, seda, persistence, fetch, jackal, cheqd, chihuahua, shentu, atomone |
| solana | 1 | solana |
| sui | 1 | sui |
| near | 1 | near |
| tron | 1 | tron |

Each chain has a `ChainMetadata` TypedDict with: name, protocol, url, symbol, decimals, coingecko_id, explorer_url, chain_id, cosmos_denom (cosmos only), cosmos_bech32_prefix (cosmos only), write_url (sui only currently).

## TOOL ARCHITECTURE (how tools work)

### Tool registration pattern
All tools are registered in `backend/tools/*.py` using `register_tool(function_schema(name, desc, properties, required), capability, executor)`. See `backend/tools/registry.py`.

### ToolContext (in `backend/tools/registry.py`)
Has: agent (dict with id, chains, capabilities, encrypted_wallets, wallet_addresses, spending_cap, total_spent_by_chain), rpc_client (PocketRPCClient), relay_tracker, db (aiosqlite), conversation_id.

### Tool discovery
`backend/tools/__init__.py` imports every tool module for side effects. New tool files must be added there.

### Chain validation
`validate_chain_allowed(context, chain)` raises ValueError if chain not in agent.chains.

### Spending cap enforcement (write tools)
`_enforce_spending_cap(context, chain, amount_native)` raises PermissionError if exceeds cap.
`_record_native_spend(context, chain, amount_native)` records after success.

### Tx confirmation scheduling
`_schedule_confirmation(context, chain, tx_hash, tool_name=..., original_tool_args=...)` spawns background polling for receipt.

### PocketRPCClient (in `backend/services/pocket_rpc.py`)
- `rpc_client.call(chain, method, params)` — generic JSON-RPC call to Pocket endpoint
- `rpc_client.get_protocol(chain)` — returns "evm"/"solana"/"cosmos"/"sui"/"near"/"tron"
- `rpc_client.get_balance(chain, address)` — native balance

## EXISTING EVM WRITE TOOLS (the template to follow)

File: `backend/tools/transaction_tools.py`

### send_transaction (native transfer — ALL protocols, 52 chains)
- EVM: `_sign_and_send_evm_transaction()` — uses eth_account.Account to sign, rpc_client.send_raw_transaction() to broadcast
- Solana: `_sign_and_send_solana_transaction()` — uses solders (Keypair, MessageV0, VersionedTransaction), System program transfer() instruction
- Tron: `_sign_and_send_tron_transaction()` — uses tronpy.keys.PrivateKey, wallet/createtransaction + wallet/broadcasttransaction RPC
- SUI: `_sign_and_send_sui_transaction()` — uses pysui (SuiConfig, SyncClient, SuiTransaction), transfer_sui() method
- Cosmos: `_sign_and_send_cosmos_transaction()` — uses cosmpy.aerial (LedgerClient, LocalWallet), ledger.send_tokens()
- NEAR: `_sign_and_send_near_transaction()` — uses py_near.account.Account, account.send_money()

### send_erc20 (EVM ONLY — needs non-EVM equivalents)
Currently returns `_unsupported_write_deferred(protocol, chain)` for non-EVM. This is what needs to change — add protocol dispatch like send_transaction already has.

### contract_call (EVM ONLY — needs non-EVM equivalents)
Same pattern — returns "deferred" for non-EVM. Read mode does eth_call; write mode signs and broadcasts.

### Wallet creation (in backend/services/wallets.py)
All 6 protocols have wallet creation functions. WRITE_PROTOCOLS = {"evm", "solana", "tron", "sui", "cosmos", "near"}. Each agent gets encrypted wallets for all write protocols at creation time via create_agent_wallets().

### Transfer services (existing patterns to follow)
- backend/services/cosmos_transfer.py — uses cosmpy.aerial (LedgerClient, LocalWallet, NetworkConfig)
- backend/services/sui_transfer.py — uses pysui (SuiConfig, SyncClient, SuiTransaction), handles coin object resolution
- backend/services/near_transfer.py — uses py_near.account.Account, account.send_money()

## THE TASK — what to build

### Part 1: Non-EVM token transfer tools (replacing the send_erc20 deferred stub)

Create protocol-specific token transfer tools. The approach should mirror how send_transaction dispatches by protocol.

#### 1a. Solana: SPL token transfers
- Standard: SPL Token program (TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA)
- Use solders library (already installed). Build SPL transfer instruction: source token account to destination token account, amount in raw units
- Need: token_mint, to_owner_address (or to_token_account), amount, decimals
- Sign with agent Solana keypair, serialize as VersionedTransaction, broadcast via rpc_client.call("solana", "sendTransaction", [raw_tx_b64, encoding base64])
- Tool: send_spl_token with params: chain (fixed solana), token_mint, to_owner_address, amount, decimals

#### 1b. Cosmos: IBC denoms / CW20 token transfers
- IBC denoms: Native Cosmos SDK bank transfers of non-staking denoms. The existing send_transaction + cosmos_transfer.py already supports this via ledger.send_tokens(recipient, amount, denom, wallet). For IBC tokens (non-native denoms), same send_tokens call works — just pass the IBC denom string.
  - Tool: send_ibc_token — params: chain, to_address, amount, denom (the IBC denom string like ibc/...)
- CW20 (CosmWasm): Smart contract tokens. Transfer requires executing a CW20 transfer message on the contract: transfer recipient/amount as a CosmWasm ExecuteMsg. Use cosmpy to sign and broadcast a contract execution.
  - Tool: send_cw20_token — params: chain, contract_address, to_address, amount

#### 1c. SUI: Move coin objects
- Standard: SUI Move 0x2::coin::Coin<T> — native SUI uses coin objects, not account balances
- Use pysui (already installed). Existing sui_transfer.py does native SUI via txer.transfer_sui(). For non-SUI coin types (e.g., USDC on SUI): use txer.split_coin() + txer.transfer_coin() or pay/pay_sui RPC methods
- Need: coin_type (the Move type string), to_address, amount
- Tool: send_sui_token — params: chain (fixed sui), coin_type, to_address, amount

#### 1d. NEAR: NEP-141 token transfers
- Standard: NEP-141 (NEAR fungible token standard)
- Use py_near (already installed). Call the FT contract ft_transfer method: account.function_call(contract_id, ft_transfer, receiver_id/amount, attached_gas, attached_deposit=1) (1 yoctoNEAR required by NEP-141)
- Tool: send_nep141_token — params: chain (fixed near), contract_id, receiver_id, amount

#### 1e. Tron: TRC-20 token transfers
- Standard: TRC-20 (Tron equivalent of ERC-20)
- Use tronpy (already installed). tronpy has contract support: client.get_contract(contract_address), then contract.transfer(to_address, amount) (this signs + broadcasts)
- Tool: send_trc20_token — params: chain (fixed tron), contract_address, to_address, amount, decimals (usually 6 for USDT on Tron)

### Part 2: Enable contract_call for non-EVM chains

Currently contract_call returns deferred for non-EVM. Extend it to support:

#### 2a. Solana: Program calls
- Solana contracts are Programs. Read: simulate transaction. Write: build instruction with program ID + data, sign, broadcast.
- Read: simulateTransaction RPC (pattern already in simulation_tools.py)
- Write: instruction with program_id, accounts list, data bytes, sign with keypair, broadcast via sendTransaction
- Params: chain, program_id, data (base58 or hex), accounts (list of pubkey/is_signer/is_writable)

#### 2b. Cosmos: CosmWasm contract calls
- Read: Query via /cosmwasm/wasm/v1/contract/{contract}/smart/{query_data} (base64 encoded query)
- Write: Execute via cosmpy LedgerClient or build Cosmos message manually with ExecuteMsg JSON
- Params: chain, contract_address, msg (CosmWasm ExecuteMsg as JSON), mode (read/write)

#### 2c. SUI: Move function calls
- Read: sui_devInspectMoveCall or pysui move call inspection
- Write: pysui SuiTransaction.move_call(target=package::module::function, arguments, type_arguments)
- Params: chain, package_object_id, module, function, arguments, type_arguments, mode

#### 2d. NEAR: Contract method calls
- Read: py_near account.view_function(contract_id, method_name, args_dict)
- Write: py_near account.function_call(contract_id, method_name, args_dict, attached_gas, attached_deposit)
- Params: chain, contract_id, method_name, args (JSON dict), mode, attached_deposit (optional)

#### 2e. Tron: Smart contract calls
- Read: tronpy contract functions.methodName(args).call() or triggerconstantcontract RPC
- Write: tronpy contract functions.methodName(args).transact() or triggerSmartContract RPC
- Params: chain, contract_address, function_signature (or abi), args, mode

## IMPLEMENTATION GUIDANCE

### Where to put the new code
- New token transfer tools: Add to backend/tools/transaction_tools.py (extend existing file) OR create backend/tools/token_transfer_tools.py and add to backend/tools/__init__.py imports.
- Non-EVM contract_call: Modify contract_call() in backend/tools/transaction_tools.py to dispatch by protocol (like send_transaction already does).
- New transfer services: Create backend/services/solana_spl_transfer.py, backend/services/cosmos_cw20_transfer.py, etc. Mirror cosmos_transfer.py, near_transfer.py, sui_transfer.py.
- Register new tools in __init__.py if you create a new tool file.
- Use try/except ImportError for relative vs absolute imports
- Use validate_chain_allowed(context, chain) for chain validation
- Use _enforce_spending_cap() and _record_native_spend() for spending caps
- Use _schedule_confirmation() after broadcasting
- Return dicts with status/chain/protocol/tx_hash/confirmation for write tools
- Use Decimal for amount math (not float)

### How to test
1. Unit test: Create backend/tests/test_non_evm_writes.py with mock RPC clients
2. Integration test: Script in tmp/ calling each tool via execute_tool() with mock context
3. Live test (read-only): contract_call read mode on non-EVM via live Pocket RPC
4. Run backend: node scripts/dev-backend.js (auto-reloads)
5. Verify tool count increases from 45

### Dependencies (ALL installed in backend/.venv)
- solders (Solana), tronpy (Tron), pysui (SUI), cosmpy (Cosmos), py_near (NEAR), eth_account (EVM)
- spl-token: may need pip install (check first)

### Important notes
- Do not broadcast real txs during testing - test guard rails only (spending_cap=0)
- Pocket RPC: https://chain-slug.api.pocket.network (READ + WRITE)
- SUI: Pocket lacks index for suix_getCoins - sui_transfer.py bootstraps from fullnode.mainnet.sui.io
- Model: meta/llama-3.1-8b-instruct - verify it can discover/call new tools
- Backend: --reload auto-restarts on file changes; .env changes need full restart
- scripts/dev-backend.js strips stale OS env vars - .env is authoritative

## STARTING INSTRUCTIONS

1. Read backend/tools/transaction_tools.py and backend/tools/registry.py
2. Read backend/services/cosmos_transfer.py, sui_transfer.py, near_transfer.py
3. Read backend/services/wallets.py for protocol wallet creation
4. Check if spl-token Python package is available
5. Implement Part 1 (non-EVM token transfers) - start with Tron TRC-20 (easiest) toward Solana SPL (hardest)
6. Implement Part 2 (non-EVM contract_call) - add protocol dispatch like send_transaction
7. Register all new tools, verify count increases from 45
8. Write tests, verify backend starts cleanly
9. Start backend and frontend, verify at http://localhost:3000

Build production-quality code following existing patterns. No placeholders, no stubs.
