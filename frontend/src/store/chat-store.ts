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

// Singleton EventSource per conversation. Re-subscribing to the same
// conversation is a no-op so React StrictMode double-mounts don't open
// duplicate streams.
let activeStream: { conversationId: string; source: EventSource } | null = null;

const openStream = (conversationId: string, accessToken: string | null) => {
  if (typeof window === "undefined") return;
  if (activeStream?.conversationId === conversationId) return;
  closeStream();
  const params = new URLSearchParams();
  if (accessToken) params.set("access_token", accessToken);
  const query = params.toString();
  const url = `/api/conversations/${encodeURIComponent(conversationId)}/stream${query ? `?${query}` : ""}`;
  const source = new EventSource(url);
  source.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload?.type === "tx_confirmation" && payload.message) {
        const incoming = payload.message as ChatMessage;
        useChatStore.setState((current) => {
          if (current.currentConversationId !== conversationId) return current;
          // De-dupe by created_at + role so a retried event doesn't append twice.
          const exists = current.messages.some(
            (m) => m.role === incoming.role && m.content === incoming.content && m.created_at === incoming.created_at,
          );
          if (exists) return current;
          return { messages: [...current.messages, clientMessage(incoming)] };
        });
      }
    } catch {
      // ignore malformed events; the heartbeat ping keeps the connection open.
    }
  };
  source.onerror = () => {
    // Browser auto-reconnects EventSource on transient errors; if the close
    // was intentional, clear the singleton so we don't keep a stale handle.
    if (source.readyState === EventSource.CLOSED) {
      closeStream();
    }
  };
  activeStream = { conversationId, source };
};

const closeStream = () => {
  if (activeStream) {
    activeStream.source.close();
    activeStream = null;
  }
};

export const teardownConversationStream = closeStream;

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
      const token = getAgentAccessToken(selectedAgentId);
      set((current) => ({
        currentConversationId: response.conversation_id,
        messages: [...current.messages, assistantMessage],
        activeChains: chains.length ? chains : current.activeChains,
      }));
      // Open the live stream for the new/updated conversation so any
      // background tx confirmations flow in automatically.
      openStream(response.conversation_id, token);
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
      openStream(id, token);
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Unable to load messages.",
      });
    } finally {
      set({ isLoading: false });
    }
  },

  createNewChat() {
    closeStream();
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
        closeStream();
        get().createNewChat();
      }
      await useAgentStore.getState().refreshConversations();
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Unable to delete conversation." });
    }
  },
}));