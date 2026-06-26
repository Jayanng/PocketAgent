"use client";

import { useEffect } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

import { AgentCard } from "@/components/agents/agent-card";
import { AgentCreator } from "@/components/agents/agent-creator";
import { AgentDetail } from "@/components/agents/agent-detail";
import { Button } from "@/components/ui/button";
import { useAgentStore } from "@/store/agent-store";

export default function AgentsPage() {
  const {
    agents,
    selectedAgentId,
    selectedAgent,
    conversations,
    balances,
    isLoadingBalances,
    isLoading,
    error,
    loadAgents,
    selectAgent,
  } = useAgentStore();

  useEffect(() => {
    void loadAgents();
  }, [loadAgents]);

  return (
    <section className="space-y-4 sm:space-y-5">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between md:items-center">
        <div className="space-y-2">
          <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">Agents</h1>
          <p className="text-sm text-muted-foreground">
            Manage autonomous agent profiles, permissions, wallets, and limits.
          </p>
        </div>
        <div className="flex w-full gap-2 sm:w-auto">
          <Button variant="secondary" size="icon" onClick={() => void loadAgents()} title="Refresh agents">
            <RefreshCw size={16} />
          </Button>
          <AgentCreator />
        </div>
      </header>

      {error && (
        <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          <AlertCircle className="mt-0.5 shrink-0" size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-12">
        <div className="space-y-3 lg:col-span-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Configured Agents</h2>
            <span className="text-xs text-muted-foreground">{agents.length} active</span>
          </div>
          <div className="space-y-3">
            {agents.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                selected={agent.id === selectedAgentId}
                onSelect={() => void selectAgent(agent.id)}
              />
            ))}
            {!agents.length && (
              <div className="rounded-lg border border-dashed border-border bg-card p-6 text-center">
                <p className="text-sm font-medium">{isLoading ? "Loading agents..." : "No agents yet."}</p>
                <p className="mt-1 text-sm text-muted-foreground">Create an agent to configure chain access and wallet limits.</p>
              </div>
            )}
          </div>
        </div>
        <div className="lg:col-span-7">
          <AgentDetail agent={selectedAgent} conversations={conversations} balances={balances} isLoadingBalances={isLoadingBalances} />
        </div>
      </div>
    </section>
  );
}
