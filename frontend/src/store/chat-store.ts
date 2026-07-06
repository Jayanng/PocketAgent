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
    const { selectedAgentId, selectedAgent, refreshConversations } =
      useAgentStore.getState();
    if (!trimmed || state.isLoading || !selectedAgentId) {
      return;
    }

    const userId = crypto.randomUUID();
    const assistantId = crypto.randomUUID();
    const userMessage: ClientMessage = {
      id: userId,
      role: "user",
      content: trimmed,
      chain_calls: [],
      tokens_used: 0,
      created_at: new Date().toISOString(),
    };
    // Append an empty assistant row immediately so the user sees a typing
    // bubble the moment they hit send; the first `text_delta` patches it.
    const emptyAssistant: ClientMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      chain_calls: [],
      tokens_used: 0,
      created_at: new Date().toISOString(),
    };

    set({
      messages: [...state.messages, userMessage, emptyAssistant],
      isLoading: true,
      activeChains: selectedAgent?.chains ?? [],
      error: null,
    });

    let totalTokens = 0;
    let finalConversationId: string | null = state.currentConversationId;
    const activeChains = new Set<string>(selectedAgent?.chains ?? []);
    let streamError: string | null = null;

    try {
      const token = getAgentAccessToken(selectedAgentId);
      await api.chat.streamMessage({
        message: trimmed,
        agentId: selectedAgentId,
        conversationId: state.currentConversationId,
        connectedWalletAddress: state.connectedWalletAddress,
        accessToken: token,
        onEvent: (event) => {
          const kind = event.event as string;
          const data = event.data;
          if (kind === "start" && typeof data.conversation_id === "string") {
            finalConversationId = data.conversation_id;
            set((cur) => ({ currentConversationId: data.conversation_id as string }));
            return;
          }
          if (kind === "text_delta" && typeof data.text === "string") {
            const t = data.text;
            set((cur) => ({
              messages: cur.messages.map((m) =>
                m.id === assistantId
                  ? { ...m, content: (m.content ?? "") + t }
                  : m,
              ),
            }));
            return;
          }
          if (kind === "tool_call") {
            const toolName = (data.name as string) ?? "unknown";
            const args = (data.args as Record<string, unknown>) ?? {};
            set((cur) => ({
              messages: cur.messages.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      chain_calls: [
                        ...m.chain_calls,
                        { tool: toolName, args } as ChainCall,
                      ],
                    }
                  : m,
              ),
            }));
            if (typeof args.chain === "string") activeChains.add(args.chain);
            if (Array.isArray(args.chains)) {
              for (const c of args.chains) {
                if (typeof c === "string") activeChains.add(c);
              }
            }
            return;
          }
          if (kind === "tool_result") {
            const toolName = (data.name as string) ?? "unknown";
            const result = data.result;
            set((cur) => ({
              messages: cur.messages.map((m) => {
                if (m.id !== assistantId) return m;
                // Patch the earliest chain_call for this tool that has no
                // result yet. If tools finish out of order, we still end up
                // with each `tool_result` mapped to a distinct chain_call column.
                let patched = false;
                const updated = m.chain_calls.map((cc) => {
                  const ccTyped = cc as { tool?: string; result?: unknown };
                  if (
                    !patched &&
                    typeof ccTyped.tool === "string" &&
                    ccTyped.tool === toolName &&
                    ccTyped.result === undefined
                  ) {
                    patched = true;
                    return { ...ccTyped, result };
                  }
                  return cc;
                });
                return { ...m, chain_calls: updated };
              }),
            }));
            return;
          }
          if (kind === "final") {
            if (typeof data.conversation_id === "string") {
              finalConversationId = data.conversation_id;
            }
            if (typeof data.tokens_used === "number") {
              totalTokens = data.tokens_used;
            }
            return;
          }
          if (kind === "error") {
            streamError = (data.detail as string) ?? "Stream error.";
            return;
          }
        },
      });

      await refreshConversations();
      set((cur) => ({
        messages: cur.messages.map((m) =>
          m.id === assistantId ? { ...m, tokens_used: totalTokens } : m,
        ),
        activeChains: activeChains.size
          ? Array.from(activeChains)
          : cur.activeChains,
        error: streamError ?? cur.error,
      }));
      // Reopen the per-conversation SSE so any pending tx_confirmation
      // events flowing from the backend arrive as chat rows.
      if (finalConversationId) {
        openStream(
          finalConversationId,
          getAgentAccessToken(selectedAgentId),
        );
      }
    } catch (error) {
      set((cur) => ({
        error:
          streamError ??
          (error instanceof Error ? error.message : "Message failed."),
        activeChains: [],
        messages: cur.messages.filter(
          (m) => m.id !== userId && m.id !== assistantId,
        ),
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