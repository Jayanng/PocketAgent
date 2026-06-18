# Agent Funding Modal — Design

**Date:** 2026-06-18
**Scope:** Replace the placeholder "Fund Agent" button (which only reveals the
address) with a modal that lets the user actually fund the agent wallet.
**Status:** Approved (offer both options; error on non-EVM connected-wallet sends;
**real mainnet native tokens on a cheap L2**, prefilled small, clearly labeled)

## Context

The current "Fund Agent" button (`agent-detail.tsx:70`) calls `fundAgent(id)`
→ `POST /api/agents/{id}/fund`, which **only returns the wallet address**
(`agents.py:130-140`). No tokens move. The build plan (Prompt 10) noted funding
"would integrate with MetaMask" — never built. So write tools (`send_transaction`
etc.) sign correctly but fail on-chain ("insufficient funds") because the agent
wallet is born empty.

## Goal

A modal that, on "Fund Agent" click, asks the user to choose:
1. **Use connected wallet** — send native tokens from the currently-connected
   EVM wallet (any wallet via RainbowKit, not just MetaMask) to the agent
   address, with a user-entered amount.
2. **Transfer manually** — copy the agent's address to fund from any external
   source (any chain, any wallet, any protocol).

The user explicitly chooses — nothing is automatic.

## Funding type — real mainnet, cheap L2 (approved)

PocketAgent reads everything via Pocket **mainnet** RPC (verified: ethereum
chain_id=1, polygon=137, zero testnets in the registry; frontend imports
`mainnet as ethereum`). A testnet faucet would fund an address the app's
mainnet reads can't see — a broken demo. So funding uses **real mainnet native
tokens on a cheap L2** (Polygon / Base / Arbitrum — all on Pocket mainnet RPC):

- Prefilled amount ~0.001, user-editable, clearly labeled "real mainnet funds".
- 0.01 POL on Polygon ≈ fractions of a cent; Base/Arbitrum gas is sub-cent.
- End-to-end consistent: Pocket mainnet RPC sees the funds → balances, writes,
  receipts all work. Showcases Pocket's actual mainnet decentralized RPC (the
  hackathon's point). Ethereum L1 is avoided (expensive gas).

The "Transfer manually" path remains free/any-source (user can also send
testnet tokens to the same address for isolated signing tests, with the caveat
that the app reads mainnet).

## Wallet infrastructure (verified present)

- `wallet-provider.tsx` wraps the app in RainbowKit + wagmi `QueryClientProvider`,
  configured for ethereum/polygon/arbitrum/optimism/bsc/avalanche/base (all EVM).
- `useAccount`, `useBalance`, `useSendTransaction`, `useSwitchChain` available
  from `wagmi ^2.19.5`.
- `connect-button.tsx` already uses the RainbowKit custom connect button — any
  EVM wallet (MetaMask, WalletConnect, Coinbase, etc.) works, not just MetaMask.
- The connected wallet address already flows to the backend via `wallet-sync.tsx`.

## Approach

### Non-EVM handling (approved: offer both, error on non-EVM)

The modal always offers both options for every agent chain. If the user picks
"Use connected wallet" for a **non-EVM chain** (e.g. solana), the modal shows a
clear error: "Connected EVM wallets can't send to Solana. Use 'Transfer
manually' to fund the Solana address from a Solana wallet." No silent failure,
no hidden behavior.

### New component — `frontend/src/components/agents/fund-agent-dialog.tsx`

A shadcn `Dialog` (matching `agent-creator.tsx`'s dialog style) with:

1. **Header**: "Fund {agent.name}" + the agent's wallet address (copyable).
2. **Chain selector**: dropdown of the agent's enabled chains (so the user
   picks which chain to fund — ethereum, polygon, solana, etc.).
3. **Amount input**: native token amount (e.g. "0.05"), with the chain's symbol
   shown.
4. **Two path buttons** (the user's explicit choice):
   - **"Send from connected wallet"** — visible only if a wallet is connected
     (`useAccount().isConnected`). Calls `useSendTransaction` with
     `to: agent.wallet_address`, `value: parseEther(amount)`, on the selected
     chain. Uses `useSwitchChain` if the connected chain ≠ selected chain.
     On non-EVM selected chain → shows the EVM-only error inline.
     On success → shows tx hash + "View on explorer" link; on failure →
     surfaces the wagmi error message.
   - **"Transfer manually"** — always available. Shows the agent address with
     a Copy button and a one-line instruction ("Send {amount} {symbol} to this
     address from any wallet"). No wallet connection needed.

### Wiring — `agent-detail.tsx`

Replace the current "Fund Agent" button's `onClick` (which calls `fundAgent`
and sets `fundingAddress`) with opening the new `FundAgentDialog`. The dialog
takes the `agent` object (for name, wallet_address, chains) as a prop. The
existing `fundAgent` store action stays (used to fetch the address if missing),
but the real funding happens client-side via wagmi for the connected path.

### Backend

**No changes.** The connected-wallet path is pure client-side (wagmi signs +
broadcasts directly to the chain via Pocket RPC, which is already wagmi's
transport in `wallet-provider.tsx`). The manual path needs no backend. The
existing `POST /api/agents/{id}/fund` (address lookup) is still used to fetch
the address if `agent.wallet_address` is absent.

## Out of scope

- Funding non-EVM chains via the connected wallet (physically impossible with
  an EVM wallet — handled by the clear error, not attempted).
- ERC-20 token funding (native token only for v1; ERC-20 is a later addition).
- Gas estimation UI (wagmi's `useSendTransaction` handles gas; MetaMask/wallet
  shows the confirmation with gas).
- Backend tests (no backend changes). Frontend is covered by lint + build.

## Completion bar

"Flawless" = `npm run lint` clean, `npm run build` clean, the modal opens on
"Fund Agent", both paths render correctly, the connected-wallet path constructs
a valid transaction for EVM chains and errors cleanly for non-EVM, the manual
path copies the address. Committed + pushed.
