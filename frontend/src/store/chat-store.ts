"use client";

import { create } from "zustand";

import {
  api,
  getAgentAccessToken,
  rememberAgentAccessToken,
  type Agent,
  type ChainCall,
  type ChatMessage,
  type Conversation,
} from "@/lib/api";

type ClientMessage = ChatMessage & {
  id: string;
  tokens_used: number;
};

type ChatState = {
  agents: Agent[];
  selectedAgentId: string | null;
  conversations: Conversation[];
  currentConversationId: string | null;
  messages: ClientMessage[];
  isLoading: boolean;
  isBootstrapping: boolean;
  activeChains: string[];
  connectedWalletAddress: string | null;
  error: string | null;
  setConnectedWalletAddress: (address: string | null) => void;
  initialize: () => Promise<void>;
  selectAgent: (agentId: string) => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  loadConversation: (id: string) => Promise<void>;
  createNewChat: () => void;
  createDefaultAgent: () => Promise<void>;
};

const DEFAULT_AGENT = {
  name: "Research Agent",
  description: "Read-only Pocket RPC assistant for balances, gas, and chain health.",
  chains: ["ethereum", "polygon", "arbitrum", "base", "optimism", "solana"],
  capabilities: ["read", "compare", "analytics"],
};

const clientMessage = (message: ChatMessage): ClientMessage => ({
  ...message,
  id: crypto.randomUUID(),
  tokens_used: message.tokens_used ?? 0,
});

const inferChains = (calls: ChainCall[]): string[] => {
  const values = new Set<string>();
  for (const call of calls) {
    const args = call.args ?? {};
    const chain = call.chain ?? (typeof args.chain === "string" ? args.chain : undefined);
    const chains = call.chains ?? (Array.isArray(args.chains) ? args.chains : undefined);
    if (chain) values.add(chain);
    if (chains) {
      for (const value of chains) {
        if (typeof value === "string") values.add(value);
      }
    }
  }
  return Array.from(values);
};

export const useChatStore = create<ChatState>((set, get) => ({
  agents: [],
  selectedAgentId: null,
  conversations: [],
  currentConversationId: null,
  messages: [],
  isLoading: false,
  isBootstrapping: true,
  activeChains: [],
  connectedWalletAddress: null,
  error: null,

  setConnectedWalletAddress(address) {
    set({ connectedWalletAddress: address });
  },

  async initialize() {
    set({ isBootstrapping: true, error: null });
    try {
      const agents = await api.agents.list();
      const firstAgent = agents[0] ?? null;
      set({ agents, selectedAgentId: firstAgent?.id ?? null });
      if (firstAgent) {
        const conversations = await api.chat.getConversations(firstAgent.id);
        set({ conversations });
      }
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Unable to load chat workspace." });
    } finally {
      set({ isBootstrapping: false });
    }
  },

  async selectAgent(agentId) {
    set({
      selectedAgentId: agentId,
      currentConversationId: null,
      messages: [],
      activeChains: [],
      error: null,
    });
    try {
      const conversations = await api.chat.getConversations(agentId);
      set({ conversations });
    } catch (error) {
      set({
        conversations: [],
        error: error instanceof Error ? error.message : "Unable to load conversations.",
      });
    }
  },

  async sendMessage(message) {
    const trimmed = message.trim();
    const state = get();
    if (!trimmed || state.isLoading || !state.selectedAgentId) {
      return;
    }

    const agent = state.agents.find((candidate) => candidate.id === state.selectedAgentId);
    const userMessage: ClientMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      chain_calls: [],
      tokens_used: 0,
      created_at: new Date().toISOString(),
    };

    set({
      messages: [...state.messages, userMessage],
      isLoading: true,
      activeChains: agent?.chains ?? [],
      error: null,
    });

    try {
      const response = await api.chat.sendMessage(
        trimmed,
        state.selectedAgentId,
        state.currentConversationId,
        state.connectedWalletAddress
      );
      const assistantMessage: ClientMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.response,
        chain_calls: response.chain_calls,
        tokens_used: response.tokens_used,
        created_at: new Date().toISOString(),
      };
      const chains = inferChains(response.chain_calls);
      const conversations = await api.chat.getConversations(state.selectedAgentId);
      set((current) => ({
        currentConversationId: response.conversation_id,
        conversations,
        messages: [...current.messages, assistantMessage],
        activeChains: chains.length ? chains : current.activeChains,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Message failed.",
        activeChains: [],
      });
    } finally {
      set({ isLoading: false });
    }
  },

  async loadConversation(id) {
    set({ isLoading: true, error: null, currentConversationId: id, activeChains: [] });
    try {
      const selectedAgentId = get().selectedAgentId;
      const token = selectedAgentId ? getAgentAccessToken(selectedAgentId) : null;
      const messages = await api.chat.getMessages(id, token);
      const normalized = messages.map(clientMessage);
      const lastAssistant = [...normalized].reverse().find((message) => message.role === "assistant");
      set({
        messages: normalized,
        activeChains: lastAssistant ? inferChains(lastAssistant.chain_calls) : [],
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Unable to load messages.",
      });
    } finally {
      set({ isLoading: false });
    }
  },

  createNewChat() {
    set({
      currentConversationId: null,
      messages: [],
      activeChains: [],
      error: null,
    });
  },

  async createDefaultAgent() {
    set({ isBootstrapping: true, error: null });
    try {
      const created = await api.agents.create(DEFAULT_AGENT);
      rememberAgentAccessToken(created.id, created.access_token);
      await get().initialize();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Unable to create agent.",
        isBootstrapping: false,
      });
    }
  },
}));
