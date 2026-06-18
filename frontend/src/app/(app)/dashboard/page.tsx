"use client";

import { ChainHealth } from "@/components/dashboard/chain-health";
import { CostTracker } from "@/components/dashboard/cost-tracker";
import { PortfolioView } from "@/components/dashboard/portfolio-view";
import { RelayStats } from "@/components/dashboard/relay-stats";

export default function DashboardPage() {
  return (
    <section className="space-y-5">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Pocket relay usage, chain activity, and cost overview — live via Pocket Network RPC.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <RelayStats />
        <ChainHealth />
        <CostTracker />
        <PortfolioView />
      </div>
    </section>
  );
}
