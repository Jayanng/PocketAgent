const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Protocol grouping (shared across dashboard components) ─────────────────
import type { ChainProtocol, ChainConfig } from "@/lib/constants";
import { CHAIN_CONFIGS } from "@/lib/constants";

/** Fixed display order for the 7 protocol families, biggest first. */
export const PROTOCOL_ORDER: ChainProtocol[] = ["evm", "cosmos", "solana", "sui", "near", "tron"];

export const PROTOCOL_LABEL: Record<ChainProtocol, string> = {
  evm: "EVM",
  cosmos: "Cosmos",
  solana: "Solana",
  sui: "Sui",
  near: "Near",
  tron: "Tron",
};

/** Look up a chain's protocol from the frontend registry. Falls back to "evm". */
export function chainProtocol(chain: string): ChainProtocol {
  const cfg = (CHAIN_CONFIGS as Record<string, ChainConfig>)[chain];
  return cfg?.protocol ?? "evm";
}

/** Group a list of chain-keyed items by protocol, in PROTOCOL_ORDER. */
export function groupByProtocol<T extends { chain: string }>(items: T[]) {
  const map = new Map<ChainProtocol, T[]>();
  for (const item of items) {
    const p = chainProtocol(item.chain);
    const list = map.get(p) ?? [];
    list.push(item);
    map.set(p, list);
  }
  return PROTOCOL_ORDER.filter((p) => map.has(p)).map((p) => ({
    protocol: p,
    label: PROTOCOL_LABEL[p],
    items: map.get(p) ?? [],
  }));
}

export type Agent = {
  id: string;
  name: string;
  description?: string | null;
  chains: string[];
  capabilities: string[];
  wallet_address?: string | null;
  spending_cap?: number;
  total_spent?: number;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

export type AgentCreateInput = {
  name: string;
  description?: string;
  chains: string[];
  capabilities: string[];
  spending_cap?: number;
};

export type AgentCreateResponse = {
  id: string;
  name: string;
  wallet_address: string;
};

export type AgentFundResponse = {
  id: string;
  wallet_address: string;
};

export type AgentBalancesResponse = {
  agent_id: string;
  wallet_address: string;
  balances: Record<string, {
    formatted?: string;
    amount?: string | number;
    amount_decimal?: number;
    symbol?: string;
    usd_value?: number | string | null;
    error?: string;
  }>;
};

export type Conversation = {
  id: string;
  title: string;
  created_at?: string | null;
};

export type ChainCall = {
  tool?: string;
  args?: Record<string, unknown>;
  result?: unknown;
  chain?: string;
  chains?: string[];
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  chain_calls: ChainCall[];
  tokens_used?: number;
  created_at?: string | null;
};

export type ChatResponse = {
  response: string;
  conversation_id: string;
  chain_calls: ChainCall[];
  tokens_used: number;
};

// ─── Analytics ──────────────────────────────────────────────────────────────

export type Timeframe = "day" | "week" | "all";

export type ChainStat = {
  chain: string;
  relays: number;
  avg_latency_ms: number;
  pokt_cost: number;
};

export type DailyUsage = {
  date: string;
  relays: number;
  pokt_cost: number;
};

export type RelayStats = {
  total_relays: number;
  avg_latency_ms: number;
  total_pokt_cost: number;
  success_rate: number;
  successful_relays: number;
  failed_relays: number;
  timeframe: Timeframe;
  per_chain: ChainStat[];
  daily_usage: DailyUsage[];
};

export type ChainHealthEntry = {
  chain: string;
  name: string;
  protocol: string;
  symbol: string;
  status: "green" | "yellow" | "red" | "registered";
  block_height: number | null;
  latency_ms: number | null;
  error: string | null;
  live: boolean;
};

export type ChainHealth = {
  checked_at: string;
  total: number;
  healthy: number;
  degraded: number;
  down: number;
  registered: number;
  live: boolean;
  chains: ChainHealthEntry[];
};

export type CostChain = {
  chain: string;
  relays: number;
  pokt_cost: number;
  share: number;
};

export type CostTracker = {
  total_pokt_cost: number;
  notional_pokt_per_relay: number;
  total_relays: number;
  per_chain: CostChain[];
  daily_trend: DailyUsage[];
  timeframe: Timeframe;
  note: string;
};

export type PortfolioHolding = {
  chain: string;
  name: string;
  symbol: string;
  protocol: string;
  raw: string | null;
  formatted: string | null;
  usd_value: number | null;
  share: number;
};

export type Portfolio = {
  address: string;
  total_usd: number;
  chains_checked: number;
  checked_at: string;
  holdings: PortfolioHolding[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let detail = `Request failed with ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail || detail;
    } catch {
      // Keep the status-only fallback.
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  chat: {
    sendMessage(
      message: string,
      agentId: string,
      conversationId: string | null,
      connectedWalletAddress: string | null
    ) {
      return request<ChatResponse>("/api/chat", {
        method: "POST",
        body: JSON.stringify({
          message,
          agent_id: agentId,
          conversation_id: conversationId,
          connected_wallet_address: connectedWalletAddress,
        }),
      });
    },
    getConversations(agentId: string) {
      return request<Conversation[]>(`/api/conversations?agent_id=${encodeURIComponent(agentId)}`);
    },
    getMessages(conversationId: string) {
      return request<ChatMessage[]>(`/api/conversations/${encodeURIComponent(conversationId)}/messages`);
    },
    deleteConversation(conversationId: string) {
      return request<void>(`/api/conversations/${encodeURIComponent(conversationId)}`, {
        method: "DELETE",
      });
    },
  },
  agents: {
    list() {
      return request<Agent[]>("/api/agents");
    },
    create(data: AgentCreateInput) {
      return request<AgentCreateResponse>("/api/agents", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    get(id: string) {
      return request<Agent>(`/api/agents/${encodeURIComponent(id)}`);
    },
    fund(id: string) {
      return request<AgentFundResponse>(`/api/agents/${encodeURIComponent(id)}/fund`, {
        method: "POST",
      });
    },
    balances(id: string) {
      return request<AgentBalancesResponse>(`/api/agents/${encodeURIComponent(id)}/balances`);
    },
    delete(id: string) {
      return request<void>(`/api/agents/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });
    },
  },
  analytics: {
    relayStats(agentId: string | null, timeframe: Timeframe = "all") {
      const params = new URLSearchParams({ timeframe });
      if (agentId) params.set("agent_id", agentId);
      return request<RelayStats>(`/api/analytics/relay-stats?${params}`);
    },
    chainHealth(live = false) {
      return request<ChainHealth>(`/api/analytics/chain-health${live ? "?live=true" : ""}`);
    },
    costTracker(agentId: string | null, timeframe: Timeframe = "all") {
      const params = new URLSearchParams({ timeframe });
      if (agentId) params.set("agent_id", agentId);
      return request<CostTracker>(`/api/analytics/cost-tracker?${params}`);
    },
    portfolio(address: string, chains?: string[]) {
      const params = new URLSearchParams({ address });
      if (chains?.length) params.set("chains", chains.join(","));
      return request<Portfolio>(`/api/analytics/portfolio?${params}`);
    },
  },
};
