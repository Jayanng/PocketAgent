export type ToolCapability = "read" | "compare" | "transact" | "analytics";

export type DocsTool = {
  name: string;
  capability: ToolCapability;
  module: string;
  description: string;
};

export const MCP_TOOL_MODULES = [
  { id: "balance_tools", label: "Balances", count: 6 },
  { id: "chain_tools", label: "Chains", count: 2 },
  { id: "compare_tools", label: "Compare", count: 3 },
  { id: "transaction_tools", label: "Transactions", count: 15 },
  { id: "token_tools", label: "Tokens", count: 13 },
  { id: "token_transfer_tools", label: "Token Transfers", count: 6 },
  { id: "simulation_tools", label: "Simulation", count: 1 },
  { id: "wallet_tools", label: "Wallet", count: 1 },
  { id: "pokt_tools", label: "POKT", count: 1 },
  { id: "analytics_tools", label: "Analytics", count: 3 },
] as const;

/** All 51 MCP tools — synced with backend TOOL_REGISTRY. */
export const MCP_TOOLS: DocsTool[] = [
  { name: "analyze_wallet", capability: "read", module: "wallet_tools", description: "Multi-chain portfolio report with CoinGecko valuations" },
  { name: "compare_balances", capability: "read", module: "balance_tools", description: "Compare native balances across chains for an address" },
  { name: "compare_chains", capability: "compare", module: "compare_tools", description: "Compare gas fees and latency across chains" },
  { name: "contract_call", capability: "transact", module: "transaction_tools", description: "Multi-protocol contract call (EVM, Solana, Cosmos, SUI, NEAR, TRON)" },
  { name: "convert_units", capability: "read", module: "balance_tools", description: "Convert between wei/lamports/uatom and human units" },
  { name: "cosmos_get_balance", capability: "read", module: "balance_tools", description: "Cosmos native balance query" },
  { name: "cosmos_get_block", capability: "read", module: "transaction_tools", description: "Fetch a Cosmos block by height" },
  { name: "cosmos_get_governance", capability: "read", module: "token_tools", description: "Cosmos governance proposals and votes" },
  { name: "cosmos_get_staking", capability: "read", module: "token_tools", description: "Cosmos staking delegations and rewards" },
  { name: "cosmos_get_transaction", capability: "read", module: "transaction_tools", description: "Fetch a Cosmos transaction by hash" },
  { name: "cosmos_get_validators", capability: "read", module: "token_tools", description: "List Cosmos validators for a chain" },
  { name: "estimate_relay_cost", capability: "analytics", module: "pokt_tools", description: "Estimate relay cost in notional POKT" },
  { name: "estimate_transaction_cost", capability: "compare", module: "compare_tools", description: "Estimate gas cost for a transaction on a chain" },
  { name: "evm_call", capability: "read", module: "token_tools", description: "Read-only EVM eth_call" },
  { name: "evm_call_contract", capability: "read", module: "token_tools", description: "Call an EVM contract method (read mode)" },
  { name: "evm_estimate_gas", capability: "read", module: "transaction_tools", description: "Estimate gas for an EVM transaction" },
  { name: "evm_get_balance", capability: "read", module: "balance_tools", description: "EVM native balance query" },
  { name: "evm_get_block", capability: "read", module: "transaction_tools", description: "Fetch an EVM block by number or hash" },
  { name: "evm_get_block_number", capability: "read", module: "transaction_tools", description: "Latest EVM block number" },
  { name: "evm_get_logs", capability: "read", module: "token_tools", description: "EVM event logs filter" },
  { name: "evm_get_receipt", capability: "read", module: "transaction_tools", description: "Transaction receipt by hash" },
  { name: "evm_get_token_info", capability: "read", module: "token_tools", description: "ERC-20 metadata (name, symbol, decimals)" },
  { name: "evm_get_transaction", capability: "read", module: "transaction_tools", description: "EVM transaction by hash" },
  { name: "get_chain_info", capability: "read", module: "chain_tools", description: "Chain metadata — RPC URL, explorer, decimals" },
  { name: "get_cost_breakdown", capability: "analytics", module: "analytics_tools", description: "Per-chain relay cost breakdown for an agent" },
  { name: "get_relay_history", capability: "analytics", module: "analytics_tools", description: "Historical relay log for an agent" },
  { name: "get_relay_stats", capability: "analytics", module: "analytics_tools", description: "Aggregated relay statistics" },
  { name: "list_chains", capability: "read", module: "chain_tools", description: "List all supported chains" },
  { name: "near_get_block", capability: "read", module: "transaction_tools", description: "NEAR block by height or hash" },
  { name: "near_get_transaction", capability: "read", module: "transaction_tools", description: "NEAR transaction status" },
  { name: "near_query", capability: "read", module: "token_tools", description: "NEAR view-function query" },
  { name: "recommend_chain", capability: "compare", module: "compare_tools", description: "Recommend optimal chain for a workload" },
  { name: "resolve_domain", capability: "read", module: "token_tools", description: "ENS / domain resolution to address" },
  { name: "send_cw20_token", capability: "transact", module: "token_transfer_tools", description: "Send CW20 tokens on Cosmos chains" },
  { name: "send_erc20", capability: "transact", module: "transaction_tools", description: "Send ERC-20 tokens on EVM chains" },
  { name: "send_ibc_token", capability: "transact", module: "token_transfer_tools", description: "IBC transfer between Cosmos chains" },
  { name: "send_nep141_token", capability: "transact", module: "token_transfer_tools", description: "Send NEP-141 fungible tokens on NEAR" },
  { name: "send_spl_token", capability: "transact", module: "token_transfer_tools", description: "Send SPL tokens on Solana" },
  { name: "send_sui_token", capability: "transact", module: "token_transfer_tools", description: "Send SUI coins or custom coin types" },
  { name: "send_transaction", capability: "transact", module: "transaction_tools", description: "Send native transfer on any supported protocol" },
  { name: "send_trc20_token", capability: "transact", module: "token_transfer_tools", description: "Send TRC-20 tokens on TRON" },
  { name: "simulate_transaction", capability: "transact", module: "simulation_tools", description: "Dry-run a transaction before broadcast" },
  { name: "solana_get_account", capability: "read", module: "token_tools", description: "Solana account info" },
  { name: "solana_get_balance", capability: "read", module: "balance_tools", description: "Solana native SOL balance" },
  { name: "solana_get_block", capability: "read", module: "transaction_tools", description: "Solana block by slot" },
  { name: "solana_get_signatures", capability: "read", module: "transaction_tools", description: "Recent signatures for an address" },
  { name: "solana_get_transaction", capability: "read", module: "transaction_tools", description: "Solana transaction by signature" },
  { name: "sui_get_balance", capability: "read", module: "balance_tools", description: "SUI native balance" },
  { name: "sui_get_coins", capability: "read", module: "token_tools", description: "List coin objects owned by an address" },
  { name: "sui_get_object", capability: "read", module: "token_tools", description: "Fetch a SUI object by ID" },
  { name: "sui_get_transaction", capability: "read", module: "transaction_tools", description: "SUI transaction by digest" },
];

export const MCP_RESOURCES = [
  { uri: "pocket://chains", description: "All supported chains with protocol metadata" },
  { uri: "pocket://chains/{chain}/status", description: "Health and latency for a specific chain" },
  { uri: "pocket://agents/{id}/stats", description: "Relay and spend statistics for an agent" },
  { uri: "pocket://agents/{id}/wallet", description: "Multi-chain wallet addresses and balances" },
  { uri: "pocket://cache/stats", description: "RPC response cache hit rates and TTL metrics" },
] as const;

export const MCP_PROMPTS = [
  { name: "analyze_wallet", description: "Multi-chain portfolio analysis with valuations" },
  { name: "find_cheapest_chain", description: "Find the lowest-fee chain for a transaction type" },
  { name: "track_pokt_costs", description: "Track and summarize relay costs in POKT" },
  { name: "compare_and_recommend", description: "Compare chains and recommend the best fit" },
] as const;