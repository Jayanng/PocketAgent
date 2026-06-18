"use client";

import { create } from "zustand";

import { api, type Agent, type AgentBalancesResponse, type AgentCreateInput, type AgentCreateResponse, type Conversation } from "@/lib/api";

type AgentState = {
  agents: Agent[];
  selectedAgentId: string | null;
  selectedAgent: Agent | null;
  conversations: Conversation[];
  balances: AgentBalancesResponse["balances"];
  isLoadingBalances: boolean;
  isLoading: boolean;
  isCreating: boolean;
  error: string | null;
  createdWalletAddress: string | null;
  loadAgents: () => Promise<void>;
  createAgent: (data: AgentCreateInput) => Promise<AgentCreateResponse>;
  deleteAgent: (id: string) => Promise<void>;
  selectAgent: (id: string | null) => Promise<void>;
  fundAgent: (id: string) => Promise<string>;
  loadBalances: (id: string) => Promise<void>;
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
  error: null,
  createdWalletAddress: null,

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
    set({ isCreating: true, error: null, createdWalletAddress: null });
    try {
      const created = await api.agents.create(data);
      set({ createdWalletAddress: created.wallet_address });
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

  async deleteAgent(id) {
    set({ error: null });
    try {
      await api.agents.delete(id);
      const nextAgents = get().agents.map((agent) => (agent.id === id ? { ...agent, is_active: false } : agent));
      set({ agents: nextAgents });
      if (get().selectedAgentId === id) {
        await get().selectAgent(id);
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
      set({
        selectedAgent: null,
        conversations: [],
        balances: {},
        error: error instanceof Error ? error.message : "Unable to load agent details.",
      });
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

  clearCreatedWalletAddress() {
    set({ createdWalletAddress: null });
  },
}));
