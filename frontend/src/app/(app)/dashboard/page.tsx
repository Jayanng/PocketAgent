"use client";

import { useEffect, useState } from "react";

import { ChainHealth } from "@/components/dashboard/chain-health";
import { CostTracker } from "@/components/dashboard/cost-tracker";
import { PortfolioView } from "@/components/dashboard/portfolio-view";
import { RelayStats } from "@/components/dashboard/relay-stats";
import { useAgentStore } from "@/store/agent-store";

export default function DashboardPage() {
  const { agents, loadAgents } = useAgentStore();
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");

  useEffect(() => {
    void loadAgents();
  }, [loadAgents]);

  const scopedAgentId = selectedAgentId || null;

  return (
    <section className="space-y-6 page-enter">
      <header className="flex flex-col gap-3 border-b border-border/40 pb-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
            </span>
            <span className="text-[10px] font-mono uppercase tracking-wider text-primary font-semibold">Active Node Listener</span>
          </div>
          <h1 className="mt-1 text-xl font-bold tracking-tight sm:text-2xl">Network Control Center</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Pocket RPC relay traffic, multi-chain performance diagnostics, and cost overview.
          </p>
        </div>
        <div className="flex flex-col gap-1 sm:min-w-[14rem]">
          <label className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Analytics scope</label>
          <select
            value={selectedAgentId}
            onChange={(e) => setSelectedAgentId(e.target.value)}
            className="h-9 rounded-lg border border-border/60 bg-background px-3 text-xs font-medium outline-none focus:border-primary/50"
          >
            <option value="">All agents (global)</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <RelayStats agentId={scopedAgentId} />
          <ChainHealth />
        </div>
        <div className="space-y-6">
          <CostTracker agentId={scopedAgentId} />
          <PortfolioView />
        </div>
      </div>
    </section>
  );
}