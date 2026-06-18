# Prompt 12 — Dashboard Page: Verify, Test, Fix & Polish

**Date:** 2026-06-18
**Scope:** Codex Prompt 12 from `PocketAgent_Build_Plan (2).md` (lines 1594–1645)
**Status:** Approved (verify + test + fix & polish)

## Context

Prompt 12's deliverables already exist end-to-end on disk and are wired together:

- **Frontend** — `frontend/src/app/(app)/dashboard/page.tsx` + 4 components:
  `relay-stats.tsx`, `chain-health.tsx`, `cost-tracker.tsx`, `portfolio-view.tsx`.
  Charts use inline SVG (matches the plan's "inline SVG — don't overcomplicate").
- **Backend** — `backend/routers/analytics.py` with 4 endpoints, all registered in
  `main.py`: `GET /api/analytics/{relay-stats,chain-health,cost-tracker,portfolio}`.
- **API client** — `frontend/src/lib/api.ts` exposes `api.analytics.*` with full TS types.
- **Service deps** verified present: `RelayTrackerService` (stats/chain/daily),
  `PriceFeedService.get_prices`, `PocketRPCClient.{get_block_number,multi_chain_balance}`.

**Gap to "flawless":** no `test_prompt12_*` test file (the repo's per-prompt pattern is
`test_prompt4`…`test_prompt8`), no verification run on record, and one code smell —
`relay_stats` reaches into the private `tracker._connect()` to compute success rate.

## Goal

Prompt 12 passes `npm run lint`, `npm run build`, and the full backend pytest suite
(including a new `test_prompt12_dashboard.py`) with zero warnings, and the success-rate
computation is moved behind a clean public method.

## Approach

### 1. Baseline verification (before any change)
- Frontend: `npm run lint`, then `npm run build` in `frontend/`.
- Backend: import-check `routers.analytics`; run existing `test_prompt4`…`test_prompt8`
  to confirm no regression baseline. No live Pocket RPC / network.

### 2. New test file — `backend/tests/test_prompt12_dashboard.py`
Pattern: `unittest.IsolatedAsyncioTestCase`, fakes, hermetic (no network/DB) — mirrors
`test_prompt8_chain_router.py`. The router builds its own `_rpc`/`_tracker`/`_prices`
internally, so tests monkeypatch those module-level factories.

Coverage:
- **`chain-health`** (`live=false`): headline chains probed, rest `registered`; counts
  (healthy/degraded/down/registered) correct; `live=true` probes all registry chains.
- **`chain-health`** status mapping: green (<8s), yellow (>8s), red on
  `asyncio.TimeoutError` / exception.
- **`portfolio`**: unknown chain → HTTP 400; USD uses RPC `usd_value` first, CoinGecko
  fallback; `total_usd` and per-holding `share` math; error entries pass through.
- **`relay-stats` / `cost-tracker`**: seed a temp on-disk sqlite `relay_logs`, assert
  totals, per-chain grouping, daily trend, notional POKT (count ×
  `NOTIONAL_POKT_PER_RELAY`), and success-rate computation.

### 3. Refactor
- Add `RelayTrackerService.get_success_rate(agent_id, timeframe) -> dict` (returns
  `{successful, failed, total, success_rate}`) computed via one SQL query.
- `analytics.relay_stats` calls it instead of `tracker._connect()` + manual loop.
  Behavior identical; the private-method access is removed.

### 4. Polish
- Fix any TypeScript/ESLint/import errors the build surfaces. No feature changes,
  no UI redesign, no new chart libraries.

## Out of scope
- Live Pocket RPC calls in tests (kept hermetic).
- UI redesign / chart-library swap.
- Prompts 13–18.

## Completion bar
"Flawless" = `npm run lint` ✅, `npm run build` ✅, backend import ✅, full pytest green
(incl. new `test_prompt12`), output shown to the user — not merely asserted.
