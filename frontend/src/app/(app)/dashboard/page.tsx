"use client";

import { ChainHealth } from "@/components/dashboard/chain-health";
import { CostTracker } from "@/components/dashboard/cost-tracker";
import { PortfolioView } from "@/components/dashboard/portfolio-view";
import { RelayStats } from "@/components/dashboard/relay-stats";

export default function DashboardPage() {
  return (
    <section className="space-y-6 page-enter">
      <header className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b border-border/40 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
            <span className="text-[10px] font-mono uppercase tracking-wider text-green-500 font-semibold">Active Node Listener</span>
          </div>
          <h1 className="mt-1 text-xl font-bold tracking-tight sm:text-2xl">Network Control Center</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Pocket RPC relay traffic, multi-chain performance diagnostics, and cost overview.
          </p>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <RelayStats />
          <ChainHealth />
        </div>
        <div className="space-y-6">
          <CostTracker />
          <PortfolioView />
        </div>
      </div>
    </section>
  );
}
