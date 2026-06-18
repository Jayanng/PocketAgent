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
  const activeAgents = agents.filter((agent) => agent.is_active);
  const inactiveAgents = agents.filter((agent) => !agent.is_active);

  useEffect(() => {
    void loadAgents();
  }, [loadAgents]);

  return (
    <section className="space-y-5">
      <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">Agents</h1>
          <p className="text-sm text-muted-foreground">
            Manage autonomous agent profiles, permissions, wallets, and limits.
          </p>
        </div>
        <div className="flex gap-2">
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
            <span className="text-xs text-muted-foreground">
              {activeAgents.length} active / {inactiveAgents.length} inactive
            </span>
          </div>
          <div className="space-y-3">
            {activeAgents.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                selected={agent.id === selectedAgentId}
                onSelect={() => void selectAgent(agent.id)}
              />
            ))}
            {!activeAgents.length && (
              <div className="rounded-lg border border-dashed border-border bg-card p-6 text-center">
                <p className="text-sm font-medium">{isLoading ? "Loading agents..." : "No agents yet."}</p>
                <p className="mt-1 text-sm text-muted-foreground">Create an agent to configure chain access and wallet limits.</p>
              </div>
            )}
            {inactiveAgents.length > 0 && (
              <div className="pt-2">
                <p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">Inactive</p>
                <div className="space-y-3 opacity-80">
                  {inactiveAgents.map((agent) => (
                    <AgentCard
                      key={agent.id}
                      agent={agent}
                      selected={agent.id === selectedAgentId}
                      onSelect={() => void selectAgent(agent.id)}
                    />
                  ))}
                </div>
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
