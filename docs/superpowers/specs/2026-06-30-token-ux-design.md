# Token UX Overhaul — Design Spec

**Date**: 2026-06-30
**Status**: Draft for review
**Owner**: pocketagent

## Context

PocketAgent lets a human create an AI agent, fund its wallet, then send chat messages that the agent turns into on-chain transactions signed and broadcast autonomously. The user only funds + chats; signing and broadcasting happen server-side without per-transaction approval. Whoever holds the agent's `access_token` effectively controls the agent's wallet.

The current token UX has four pain points:

1. **Lost on browser close** — tokens live in `sessionStorage`; closing the tab wipes them.
2. **Can't move across devices** — tokens are stuck on one browser/device.
3. **User doesn't know it matters** — the token is auto-stashed silently.
4. **No recovery path** — losing a token means losing access to the agent.

This design addresses all four pain points while preserving the existing token-based auth model.

## Approach

**Polished token-based (Option A)** — keep the opaque JWT-style token, evolve the UX, add a recovery path.

Rejected alternatives:
- **SIWE wallet auth** — EVM-only by definition.
- **HTTP-only sessions** — doesn't help cross-device.
- **Full multi-chain wallet auth** — much larger lift.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (frontend)                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Token Store  │  │ Tab Sync     │  │ UI Surfaces      │  │
│  │ (localStorage│  │ (Broadcast-  │  │ • Create Modal   │  │
│  │  + in-memory │◄─┤  Channel)    │  │ • Detail Panel   │  │
│  │  Map)        │  └──────────────┘  │ • Import Dialog  │  │
│  └──────────────┘                    └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                       │  X-Agent-Access-Token
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend (FastAPI)                                          │
│  ┌──────────────────┐  ┌────────────────────┐               │
│  │ existing auth    │  │ NEW: reissue-token │               │
│  │ verify_agent_    │  │ endpoint           │               │
│  │ access_token()   │  │ POST /api/agents/  │               │
│  │ (unchanged)      │  │ {id}/reissue-token │               │
│  └──────────────────┘  └────────────────────┘               │
│           │                         │                        │
│           ▼                         ▼                        │
│  ┌──────────────────────────────────────────────┐            │
│  │ SQLite (existing)                            │            │
│  │ agents table (additive migration)            │            │
│  │  - access_token_hash                         │            │
│  │  - access_token_created_at (new)             │            │
│  │  - access_token_revoked_at (new, nullable)   │            │
│  └──────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### What stays the same

- Token format (opaque JWT-style string).
- `verify_agent_access_token()` logic.
- `POST /api/agents` (still creates agent + returns initial token).
- `X-Agent-Access-Token` header and `?access_token=` SSE query param.
- All existing 119 tests.

### What changes

| Layer | Change |
|---|---|
| Storage | `sessionStorage` → `localStorage` |
| Sync | `BroadcastChannel('pocketagent:tokens')` for cross-tab updates |
| Creation UX | Mandatory modal: shows token once, copy/download/acknowledge |
| Detail UX | "Access Token" panel: view masked token, copy, rotate, export |
| Import | Dialog: paste token + agent ID, validates against backend |
| Backend | New `POST /api/agents/{id}/reissue-token` and `GET /api/agents/{id}/reissue-challenge` |
| DB | Add `access_token_created_at`, `access_token_revoked_at` columns |

### Key design decisions

1. **localStorage over sessionStorage** — persistence over per-tab isolation.
2. **Wallet signature proves ownership for reissue** — works for all 6 chains.
3. **Token rotation invalidates old token immediately** — one valid token at a time.
4. **Token remains plaintext client-side** — same as today.
5. **No silent auto-rotation** — user explicitly clicks "Rotate".
6. **Plaintext JSON for export** — threat model is cross-device for the user themselves.
7. **Block-until-acknowledged modal** — only chance the user sees the token.
8. **Rotate button on the agent detail panel** — contextually close to the agent.
9. **All 6 chains supported in v1** for wallet-signature reissue.
10. **5-minute replay protection window**.
11. **Public-with-proof-only authentication** for the reissue endpoint.

## Backend Changes

### New endpoint: `POST /api/agents/{agent_id}/reissue-token`

**Mode 1: `current_token`** (used by "Rotate")
```json
{
  "proof": {
    "type": "current_token",
    "token": "<current access_token>"
  }
}
```

**Mode 2: `wallet_signature`** (used by "Reissue" — user lost the token)
```json
{
  "proof": {
    "type": "wallet_signature",
    "chain": "ethereum" | "solana" | "sui" | "near" | "cosmos" | "tron",
    "message": "pocketagent:reissue:<agent_id>:<unix-timestamp>",
    "signature": "<chain-specific encoding>",
    "public_key": "<chain-specific encoding>"
  }
}
```

**Response** (200):
```json
{
  "access_token": "<new token>",
  "access_token_created_at": "2026-06-30T12:34:56Z",
  "agent": { ...full agent object... }
}
```

**Errors**:

| Status | When |
|---|---|
| 400 | Malformed proof / missing field |
| 401 | Invalid signature or token mismatch |
| 404 | Agent not found |
| 410 | Agent soft-deleted |
| 422 | Timestamp out of range (5-min window) |
| 503 | `ENCRYPTION_KEY` not configured |

**Endpoint behavior**:

1. Look up agent by ID.
2. Validate proof (hash comparison for `current_token`; chain-specific signature verification for `wallet_signature`).
3. Check replay protection: `abs(now - timestamp) < 300s` (only for `wallet_signature`).
4. Generate new token.
5. Update `access_token_hash` and `access_token_created_at`.
6. Return new token + agent.

Old token is invalidated implicitly — its hash no longer matches.

### New endpoint: `GET /api/agents/{agent_id}/reissue-challenge`

Returns the canonical message the user must sign.

**Response** (200):
```json
{
  "message": "pocketagent:reissue:<agent_id>:<unix-timestamp>",
  "timestamp": 1740000000
}
```

**Errors**: 404 (agent not found), 410 (agent soft-deleted).

### Database schema change

```sql
ALTER TABLE agents ADD COLUMN access_token_created_at TIMESTAMP;
ALTER TABLE agents ADD COLUMN access_token_revoked_at  TIMESTAMP;
```

Migration semantics:
- Existing agents: backfill `access_token_created_at = created_at`.
- `access_token_revoked_at` stays NULL for current valid tokens.
- Idempotent — running twice does not error.

### New file: `backend/services/wallet_signing.py`

Single entry point dispatches per chain:

```python
def verify_wallet_signature(
    chain: str,
    message: str | bytes,
    signature: str,
    public_key: str | None,
    expected_address: str,
) -> bool:
    if chain in EVM_CHAINS:
        return _verify_evm(message, signature, expected_address)
    if chain == "solana":
        return _verify_solana(message, signature, public_key, expected_address)
    if chain == "sui":
        return _verify_sui(message, signature, public_key, expected_address)
    if chain == "near":
        return _verify_near(message, signature, public_key, expected_address)
    if chain == "cosmos":
        return _verify_cosmos(message, signature, public_key, expected_address)
    if chain == "tron":
        return _verify_tron(message, signature, expected_address)
    raise ValueError(f"unsupported chain for signing: {chain}")
```

Per-chain signing schemes:

| Chain | Scheme | Library call |
|---|---|---|
| EVM | secp256k1 + EIP-191 prefix | `eth_account.Account.recover_message` |
| Solana | Ed25519, base58 pubkey | `solders.signature.Signature.verify` + `solders.pubkey.Pubkey` |
| Sui | Ed25519 with sui intent bytes (`\x00\x00\x00` + bcs message) | `pysui.sui.sui_crypto.SuiKeyPair` |
| NEAR | Ed25519, NEAR-specific prefix (`\x00\x00\x00\x00` + msg) | py-near bindings or nacl |
| Cosmos | secp256k1 ADR-036 (sha256-prefixed arbitrary-length msg) | `cosmpy.crypto.PublicKey.verify` |
| TRON | secp256k1 with TRON prefix (`\x19TRON Signed Message:\n` + len) | manual ecrecover with TRON curve params |

### New file: `backend/services/agent_token_service.py`

- `generate_access_token()` — opaque random token.
- `hash_access_token(token)` — SHA-256 hex.
- `verify_proof(agent, proof)` — dispatches between `current_token` and `wallet_signature`.
- `issue_new_token(agent_id, db_update_fn)` — generates + persists.

Existing `verify_agent_access_token()` stays unchanged.

## Frontend Changes

### New file structure

```
frontend/src/
├── lib/
│   ├── api.ts                          # unchanged API surface
│   ├── agent-auth.ts                   # EXTENDED
│   └── token-store.ts                  # NEW
├── components/
│   ├── tokens/                         # NEW directory
│   │   ├── token-display-modal.tsx
│   │   ├── token-panel.tsx
│   │   ├── token-import-dialog.tsx
│   │   ├── token-rotate-dialog.tsx
│   │   └── *.test.tsx
│   └── agents/
│       ├── agent-create-dialog.tsx     # MODIFIED
│       └── agent-detail.tsx            # MODIFIED
└── store/
    └── agent-store.ts                  # MODIFIED
```

### New: `lib/token-store.ts`

```typescript
interface TokenStore {
  get(agentId: string): string | null
  set(agentId: string, token: string): void
  forget(agentId: string): void
  has(agentId: string): boolean
  exportAll(): TokenBundle
  importOne(agentId: string, token: string): void
  importMany(bundle: TokenBundle): { ok: number; failed: string[] }
  onChange(listener: (event: TokenChangeEvent) => void): () => void
}
```

- `localStorage['pocketagent:agent-token:<id>']` for persistence.
- In-memory `Map<string, string>` for hot-path reads.
- `BroadcastChannel('pocketagent:tokens')` for cross-tab sync.
- Quota-error fallback to in-memory only.

Export format (plaintext JSON, v1):
```json
{
  "version": 1,
  "exportedAt": "2026-06-30T12:00:00Z",
  "tokens": [
    {"agentId": "abc-123", "token": "..."}
  ]
}
```

### New: `components/tokens/token-display-modal.tsx`

Shown once after agent creation. Block-until-acknowledged. Copy / Download / eye toggle / checkbox.

### New: `components/tokens/token-panel.tsx`

Three states: active, missing, recently rotated. Mounted on agent detail page.

### New: `components/tokens/token-import-dialog.tsx`

Two tabs: paste token, or sign with wallet to reissue.

### New: `components/tokens/token-rotate-dialog.tsx`

Confirmation + wallet-sign (or current-token) proof. Calls same backend endpoint as reissue.

### Modified: `lib/api.ts`

Wire request helper to `TokenStore.get()`. Add `api.agents.reissue` and `api.agents.reissueChallenge` methods.

### Modified: `store/agent-store.ts`

Three new actions:
```typescript
rotateAgentAccessToken(agentId: string): Promise<void>
importAgentAccessToken(agentId: string, token: string): Promise<boolean>
exportAllAgentTokens(): void  // triggers download
```

## Data Flows

### Flow A: Create agent

```
[Create Agent form] → POST /api/agents → token returned
   ↓
[TokenStore.set + BroadcastChannel]
   ↓
[TokenDisplayModal opens — block until acknowledged]
   ↓
[Modal closes → user lands on agent detail with TokenPanel active]
```

### Flow B: Use agent

```
[Request] → TokenStore.get → X-Agent-Access-Token header
   ↓
[verify_agent_access_token: hash check + revoked_at check]
   ↓
[200 OK] or [403 Forbidden]
```

### Flow C: Recover lost token

```
[Agent detail, no token] → "Access token required" banner
   ↓
[Sign with wallet to reissue]
   ↓
[GET /api/agents/{id}/reissue-challenge → { message, timestamp }]
   ↓
[Wallet signs message]
   ↓
[POST /api/agents/{id}/reissue-token with proof = wallet_signature]
   ↓
[Backend verifies signature → issues new token]
   ↓
[TokenStore.set + TokenDisplayModal shows new token]
```

### Flow D: Rotate token

```
[TokenPanel → Rotate]
   ↓
[POST /api/agents/{id}/reissue-token with proof = current_token]
   ↓
[New token returned → TokenStore.set → TokenDisplayModal]
```

### Flow E: Cross-tab sync

`BroadcastChannel` propagates `set`/`forget` events silently across tabs.

### Flow F: Export for cross-device

```
[Export → download JSON] → transfer file → other device: import
   ↓
[For each token: GET /api/agents/{id} to validate → save if 200, mark rejected if 403]
```

### Edge cases

| Case | Behavior |
|---|---|
| Rotation race (two tabs) | Second tab gets 401 "Token mismatch" → UI: "Rotated elsewhere, reload" |
| SSE reconnection after rotation | Brief interruption; chat-store reconnects with new token |
| Network drop during rotate | Don't auto-retry; toast: "Re-fetch via wallet signature" |
| User rejects signature | Frontend catches → toast: "Signature cancelled" |
| localStorage quota exceeded | Fallback to in-memory; one-time warning |
| BroadcastChannel unsupported | Fallback to `storage` event |
| Clock skew | Server `abs(now - T) < 300s` rejects |
| Imported token already rotated | Marked rejected; UI offers wallet-signature reissue |

## Error Handling

### Frontend error display

Single helper `api.handleError(response)`:
1. Parses `detail`.
2. Maps known errors to user-friendly messages.
3. Returns typed `ApiError`.

UI placement:
- **Toast** for transient errors.
- **Inline** for errors in modals/dialogs.
- **Full-page banner** for unrecoverable auth errors.

### Recovery tiers

**Tier 1 (transient)**: Auto-retry once after 1s. On second failure: "Request failed. [Retry] [Cancel]"
**Tier 2 (recoverable)**: "Access token invalid. [Re-import] [Sign with wallet to reissue]"
**Tier 3 (unrecoverable)**: "This agent is no longer accessible. [Remove from list]"

### Logging

Backend logs every reissue attempt with structured fields:
```json
{
  "event": "token_reissue_attempt",
  "agent_id": "...",
  "proof_type": "current_token" | "wallet_signature",
  "chain": "ethereum",
  "outcome": "success" | "invalid_proof" | "expired" | "agent_not_found" | "internal_error",
  "duration_ms": 23
}
```

## Testing Strategy

### Backend unit tests

**`tests/test_wallet_signing.py`** — all 6 chain verifiers. Parametrized: valid, invalid, wrong address, malformed, empty. Plus one known-good vector per chain.

**`tests/test_agent_token_service.py`** — generation uniqueness, hash determinism, proof verification.

**`tests/test_reissue_endpoint.py`** — endpoint behavior. Success + all failure modes (parametrized).

**`tests/test_reissue_challenge_endpoint.py`** — challenge generation.

**Database migration test** — new columns exist; backfill works; idempotent.

### Backend integration tests

**`tests/test_reissue_flow.py`** — full lifecycle (create → reissue current_token → reissue wallet_signature → old token rejected).

### Frontend tests (Vitest + RTL)

New deps: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `jsdom`.

Coverage: `token-store`, four components, store actions.

### Manual QA checklist

1. Happy path (create → use → use)
2. Multi-tab sync
3. Cross-session persistence
4. Recovery via wallet-signature
5. Rotation
6. Export/import
7. Error messaging
8. Two-tab race

### Test fixtures

```
tests/fixtures/wallet_signing/
├── evm.json
├── solana.json
├── sui.json
├── near.json
├── cosmos.json
└── tron.json
```

Throwaway keys with zero funds.

## Migration Notes

- DB schema migration is **additive** (two nullable columns). Existing agents continue to work.
- Existing 119 tests continue to pass.
- No breaking API changes — reissue and challenge endpoints are new additions.

## Out of Scope

- **Browser-cleared localStorage** — user falls back to manual import + wallet reissue.
- **Tokens on shared computers** — inherent to localStorage model.
- **Token expiry / refresh tokens** — tokens remain long-lived.
- **Auto-rotation** — user explicitly rotates.
- **Encryption of exported tokens** — plaintext JSON only.

## Open Questions

None — all resolved during brainstorming.

## Decision Log

| Decision | Choice | Rationale |
|---|---|---|
| Storage backend | localStorage | Survives close/reopen |
| Reissue proof | Wallet signature (any of 6 chains) | All chains supported natively |
| Token rotation | Immediate invalidation | Cleaner mental model |
| Modal dismissal | Block until "I saved it" checked | Only chance user sees the token |
| Frontend tests | Vitest + React Testing Library | Sets up testing foundation |
| Export format | Plaintext JSON | Threat model is cross-device for the user |
| MVP scope | All 6 chains in v1 | No half-baked state |
| Replay window | 5 minutes | Standard sweet spot |
| Endpoint auth | Public-with-proof-only | Proof IS the auth |
| Reissue flow | Separate challenge endpoint | Transparency |
| Rotation race | 401 "token mismatch" | Simple is fine |
| Export extension | .json | Universal |
| Auto-retry on transient | Yes, once after 1s | Better UX |
| Tier 3 "remove from list" | Just local view, server record stays | User might recover later |
| Stale-imported-token | Proactive offer of wallet reissue | One less back-and-forth |
