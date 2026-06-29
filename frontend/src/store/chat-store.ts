"use client";

import { create } from "zustand";

import {
  api,
  getAgentAccessToken,
  type ChainCall,
  type ChatMessage,
} from "@/lib/api";
import { useAgentStore } from "@/store/agent-store";

type ClientMessage = ChatMessage & {
  id: string;
  tokens_used: number;
};

type ChatState = {
  currentConversationId: string | null;
  messages: ClientMessage[];
  isLoading: boolean;
  isBootstrapping: boolean;
  activeChains: string[];
  connectedWalletAddress: string | null;
  error: string | null;
  setConnectedWalletAddress: (address: string | null) => void;
  initialize: () => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  loadConversation: (id: string) => Promise<void>;
  createNewChat: () => void;
  deleteConversation: (id: string) => Promise<void>;
  refreshWorkspace: () => Promise<void>;
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

  async refreshWorkspace() {
    await useAgentStore.getState().loadAgents();
  },

  async initialize() {
    set({ isBootstrapping: true, error: null });
    try {
      await useAgentStore.getState().loadAgents();
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Unable to load chat workspace." });
    } finally {
      set({ isBootstrapping: false });
    }
  },

  async sendMessage(message) {
    const trimmed = message.trim();
    const state = get();
    const { selectedAgentId, selectedAgent, refreshConversations } = useAgentStore.getState();
    if (!trimmed || state.isLoading || !selectedAgentId) {
      return;
    }

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
      activeChains: selectedAgent?.chains ?? [],
      error: null,
    });

    try {
      const response = await api.chat.sendMessage(
        trimmed,
        selectedAgentId,
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
      await refreshConversations();
      set((current) => ({
        currentConversationId: response.conversation_id,
        messages: [...current.messages, assistantMessage],
        activeChains: chains.length ? chains : current.activeChains,
      }));
    } catch (error) {
      set((current) => ({
        error: error instanceof Error ? error.message : "Message failed.",
        activeChains: [],
        messages: current.messages.filter((m) => m.id !== userMessage.id),
      }));
    } finally {
      set({ isLoading: false });
    }
  },

  async loadConversation(id) {
    set({ isLoading: true, error: null, currentConversationId: id, activeChains: [] });
    try {
      const selectedAgentId = useAgentStore.getState().selectedAgentId;
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

  async deleteConversation(id) {
    const selectedAgentId = useAgentStore.getState().selectedAgentId;
    const token = selectedAgentId ? getAgentAccessToken(selectedAgentId) : null;
    set({ error: null });
    try {
      await api.chat.deleteConversation(id, token);
      if (get().currentConversationId === id) {
        get().createNewChat();
      }
      await useAgentStore.getState().refreshConversations();
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Unable to delete conversation." });
    }
  },
}));