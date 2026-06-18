# Pocket Shannon Batch Audit

Date: 2026-06-15

## Batch Status

1. Batch 1 (endpoint corrections): Complete
2. Batch 2 (chain expansion): Complete for Phase 1 EVM set
3. Batch 3 (failover redesign): Complete
4. Batch 4 (old-reference cleanup): Complete in repo + external build plan file
5. Batch 5 (runtime notes implementation): Complete
6. Batch 6 (verification audit): Complete

## Verification Notes

- Legacy `*.gateway.pokt.network` and `backup.api.pocket.network` references were removed from the codebase.
- Shannon endpoint format is now used for backend + frontend chain endpoint registries.
- Backup gateway keys were removed and replaced by `POCKET_API_BASE`/`pocket_api_base`.
- `PocketRPCClient` now:
  - rejects `eth_subscribe` with polling guidance,
  - rate limits requests per chain (~30 req/s),
  - retries with exponential backoff on 429/503/5xx,
  - uses a single Shannon endpoint per chain (no fake backup domain).
- Runtime startup logs explicitly note public Pocket RPC usage without API keys.
- Smoke test passed: `python test_rpc.py` -> `Ethereum chain ID: 0x1`.
