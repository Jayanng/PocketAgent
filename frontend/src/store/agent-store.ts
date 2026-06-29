"use client";

import { create } from "zustand";

import {
  api,
  forgetAgentAccessToken,
  rememberAgentAccessToken,
  type Agent,
  type AgentBalancesResponse,
  type AgentCreateInput,
  type AgentCreateResponse,
  type AgentUpdateInput,
  type Conversation,
} from "@/lib/api";

type AgentState = {
  agents: Agent[];
  selectedAgentId: string | null;
  selectedAgent: Agent | null;
  conversations: Conversation[];
  balances: AgentBalancesResponse["balances"];
  isLoadingBalances: boolean;
  isLoading: boolean;
  isCreating: boolean;
  isUpdating: boolean;
  error: string | null;
  createdWalletAddress: string | null;
  createdWalletAddresses: Record<string, string>;
  createdAccessToken: string | null;
  loadAgents: () => Promise<void>;
  createAgent: (data: AgentCreateInput) => Promise<AgentCreateResponse>;
  updateAgent: (id: string, data: AgentUpdateInput) => Promise<Agent>;
  deleteAgent: (id: string) => Promise<void>;
  selectAgent: (id: string | null) => Promise<void>;
  refreshConversations: () => Promise<void>;
  fundAgent: (id: string) => Promise<string>;
  loadBalances: (id: string) => Promise<void>;
  importAgentAccessToken: (id: string, token: string) => Promise<boolean>;
  clearCreatedWalletAddress: () => void;
};

export const useAgentStore = create<AgentState>((set, get) => ({
  agents: [],
  selectedAgentId: null,
  selectedAgent: null,
  conversations: [],
  balances: {},
  isLoadingBalances: false,
  isLoading: false,
  isCreating: false,
  isUpdating: false,
  error: null,
  createdWalletAddress: null,
  createdWalletAddresses: {},
  createdAccessToken: null,

  async loadAgents() {
    set({ isLoading: true, error: null });
    try {
      const agents = await api.agents.list();
      set({ agents });
      const selectedId = get().selectedAgentId ?? agents[0]?.id ?? null;
      if (selectedId) {
        await get().selectAgent(selectedId);
      }
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Unable to load agents." });
    } finally {
      set({ isLoading: false });
    }
  },

  async createAgent(data) {
    set({ isCreating: true, error: null, createdWalletAddress: null, createdWalletAddresses: {}, createdAccessToken: null });
    try {
      const created = await api.agents.create(data);
      rememberAgentAccessToken(created.id, created.access_token);
      set({
        createdWalletAddress: created.wallet_address,
        createdWalletAddresses: created.wallet_addresses ?? {},
        createdAccessToken: created.access_token,
      });
      await get().loadAgents();
      await get().selectAgent(created.id);
      return created;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to create agent.";
      set({ error: message });
      throw new Error(message);
    } finally {
      set({ isCreating: false });
    }
  },

  async updateAgent(id, data) {
    set({ isUpdating: true, error: null });
    try {
      const updated = await api.agents.update(id, data);
      set((state) => ({
        agents: state.agents.map((agent) => (agent.id === id ? { ...agent, ...updated } : agent)),
        selectedAgent: state.selectedAgentId === id ? updated : state.selectedAgent,
      }));
      return updated;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to update agent.";
      set({ error: message });
      throw new Error(message);
    } finally {
      set({ isUpdating: false });
    }
  },

  async deleteAgent(id) {
    set({ error: null });
    try {
      await api.agents.delete(id);
      forgetAgentAccessToken(id);
      const nextAgents = get().agents.filter((agent) => agent.id !== id);
      set({ agents: nextAgents });
      if (get().selectedAgentId === id) {
        await get().selectAgent(nextAgents[0]?.id ?? null);
      }
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Unable to delete agent." });
    }
  },

  async selectAgent(id) {
    set({ selectedAgentId: id, error: null });
    if (!id) {
      set({ selectedAgent: null, conversations: [], balances: {} });
      return;
    }
    try {
      const [agent, conversations] = await Promise.all([
        api.agents.get(id),
        api.chat.getConversations(id).catch(() => []),
      ]);
      set({ selectedAgent: agent, conversations, balances: {} });
    } catch (error) {
      const summary = get().agents.find((agent) => agent.id === id) ?? null;
      set({
        selectedAgent: summary,
        conversations: [],
        balances: {},
        error: error instanceof Error ? error.message : "Unable to load agent details.",
      });
    }
  },

  async refreshConversations() {
    const id = get().selectedAgentId;
    if (!id) return;
    try {
      const conversations = await api.chat.getConversations(id);
      set({ conversations });
    } catch {
      set({ conversations: [] });
    }
  },

  async fundAgent(id) {
    set({ error: null });
    try {
      const response = await api.agents.fund(id);
      return response.wallet_address;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load funding address.";
      set({ error: message });
      throw new Error(message);
    }
  },

  async loadBalances(id) {
    set({ isLoadingBalances: true, error: null });
    try {
      const response = await api.agents.balances(id);
      set({ balances: response.balances });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Unable to load balances." });
    } finally {
      set({ isLoadingBalances: false });
    }
  },

  async importAgentAccessToken(id, token) {
    const trimmed = token.trim();
    if (!trimmed) {
      set({ error: "Access token is required." });
      return false;
    }
    set({ isLoading: true, error: null });
    try {
      const agent = await api.agents.get(id, trimmed);
      rememberAgentAccessToken(id, trimmed);
      const conversations = await api.chat.getConversations(id, trimmed).catch(() => []);
      set({ selectedAgentId: id, selectedAgent: agent, conversations, balances: {} });
      return true;
    } catch (error) {
      set({ error: error instanceof Error ? error.message : "Unable to verify access token." });
      return false;
    } finally {
      set({ isLoading: false });
    }
  },

  clearCreatedWalletAddress() {
    set({ createdWalletAddress: null, createdWalletAddresses: {}, createdAccessToken: null });
  },
}));