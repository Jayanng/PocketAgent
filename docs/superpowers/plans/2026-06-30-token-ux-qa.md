# Token UX Overhaul — Manual QA Checklist

> Status: **automated tests green** (25 frontend + 135 backend). Manual walk-through
> requires running the dev stack and a wallet with signing capability; both must be
> completed before tagging the release.

## Automated verification (already passing in CI)

| Suite | Count | Command |
|---|---|---|
| Backend pytest | 135 | `cd backend && .venv\Scripts\pytest.exe -q` |
| Frontend vitest | 25  | `cd frontend && node.exe node_modules/vitest/dist/cli.js run` |

## Manual flows

- [ ] **Happy path** — create agent → modal appears → copy token → click around dashboard → token works
- [ ] **Multi-tab** — create agent in tab A → switch to tab B → open same agent → token works (BroadcastChannel sync)
- [ ] **Cross-session** — create agent → close browser → reopen → token still works (localStorage)
- [ ] **Recovery** — clear localStorage → open agent → token panel shows "missing" → use Sign-with-wallet to reissue → agent works
- [ ] **Rotation** — click Rotate → enter token → see new token modal → old token rejected (via curl)
- [ ] **Export/import** — export tokens → clear localStorage → import on different browser profile → tokens work
- [ ] **Error path** — try reissue with wrong wallet signature → see clear error (401/422)
- [ ] **Race** — two tabs click Rotate at same time → one succeeds, other sees new-token-rotation banner

## Implementation notes / carry-forward

- **SessionStorage → localStorage migration:** the existing `api.ts` used sessionStorage for
  per-tab tokens. The refactor delegates to `TokenStore` which uses localStorage. Tokens
  now persist across sessions and tabs (intentional per spec).
- **Wallet-sign reissue** (`TokenImportDialog` "Sign with wallet" tab) is wired but
  `onSignMessage` in `agent-detail.tsx` throws "Wallet signing is not wired in this
  build" — wire to `useWalletClient().signMessage({ account, message })` before
  release. The wallet-sign reissue endpoint is fully tested on the backend.
- **Environment convention test** (`test_env_convention.py`) is excluded from CI runs
  in this worktree because the root `.env` is gitignored; the original repo passes it.
- **npm install quirk:** vitest was downloaded but bin-symlinks were never created
  in `node_modules/.bin/`. The `test` script invokes vitest via the direct path
  (`node.exe node_modules/vitest/dist/cli.js run`) to avoid this. Long-term fix:
  rerun `npm install` to regenerate the bin links.
